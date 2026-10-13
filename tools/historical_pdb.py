"""Read-only MSF7/PDB inventory, matched to its PE by GUID and age.

Exports selected CodeView records, not a complete DIA/PDB implementation.
Record layouts follow LLVM's PDB/CodeView documentation. No registry changes.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import struct
import uuid

import pefile


class Msf:
    def __init__(self,path):
        self.raw=pathlib.Path(path).read_bytes()
        if self.raw[:32]!=b'Microsoft C/C++ MSF 7.00\r\n\x1aDS\0\0\0':raise ValueError('Expected MSF7')
        block,_,blocks,size,_,mapping=struct.unpack_from('<6I',self.raw,32)
        if block not in (512,1024,2048,4096) or blocks*block!=len(self.raw):raise ValueError('Invalid MSF block geometry')
        self.block=block
        def pages(at,count):
            result=struct.unpack_from('<'+str(count)+'I',self.raw,at)
            if any(p>=blocks for p in result):raise ValueError('MSF page outside file')
            return result
        def gather(indices,length):return b''.join(self.raw[p*block:(p+1)*block] for p in indices)[:length]
        directory=gather(pages(mapping*block,(size+block-1)//block),size)
        n=struct.unpack_from('<I',directory)[0]
        sizes=struct.unpack_from('<'+str(n)+'I',directory,4)
        at=4+4*n;self.streams=[]
        for size in sizes:
            count=0 if size==0xffffffff else (size+block-1)//block
            indices=struct.unpack_from('<'+str(count)+'I',directory,at) if count else ()
            if any(p>=blocks for p in indices):raise ValueError('Stream page outside file')
            at+=4*count;self.streams.append(None if size==0xffffffff else gather(indices,size))
        self.guid=str(uuid.UUID(bytes_le=self.streams[1][12:28]))
        self.age=struct.unpack_from('<I',self.streams[1],8)[0]


def records(data,start=0,end=None):
    end=len(data) if end is None else end;at=start
    while at<end:
        if at+4>end:raise ValueError('Truncated CodeView header')
        size,kind=struct.unpack_from('<HH',data,at)
        if size<2 or at+size+2>end:raise ValueError('Truncated CodeView record')
        yield at,kind,data[at:at+size+2]
        at+=size+2


def numeric(data,at):
    kind=struct.unpack_from('<H',data,at)[0]
    if kind<0x8000:return kind,at+2
    formats={0x8000:'b',0x8001:'h',0x8002:'H',0x8003:'i',0x8004:'I',0x8009:'q',0x800a:'Q'}
    if kind not in formats:raise ValueError('Unsupported integer numeric leaf '+hex(kind))
    fmt='<'+formats[kind];return struct.unpack_from(fmt,data,at+2)[0],at+2+struct.calcsize(fmt)


def cstring(data,at):
    end=data.index(0,at);return data[at:end].decode('utf-8',errors='replace'),end+1


def fieldlist(types,index,seen=None):
    """Decode known field-list leaves; fail on unknown leaves, never guess offsets."""
    seen=set() if seen is None else seen
    if not index:return []
    if index in seen:raise ValueError('Cyclic field-list continuation')
    seen.add(index);kind,data=types[index]
    if kind!=0x1203:raise ValueError('Expected field list')
    at=4;out=[]
    while at<len(data):
        if data[at]>=0xf0:
            count=data[at]&15
            if not count:raise ValueError('Invalid CodeView padding')
            at+=count;continue
        kind=struct.unpack_from('<H',data,at)[0]
        if kind in (0x150d,0x1400):
            attr,typ=struct.unpack_from('<HI',data,at+2);offset,end=numeric(data,at+8)
            if kind==0x150d:name,at=cstring(data,end)
            else:name='<base>';at=end
            out.append(dict(name=name,type_index=typ,offset=offset,attributes=attr,base=kind==0x1400))
        elif kind in (0x150e,0x150f,0x1510,0x1512):
            _,at=cstring(data,at+8)
        elif kind==0x1511:
            attr=struct.unpack_from('<H',data,at+2)[0]
            _,at=cstring(data,at+8+(4 if (attr>>2)&7 in (4,6) else 0))
        elif kind==0x1409:at+=8
        elif kind==0x1404:
            target=struct.unpack_from('<I',data,at+4)[0];out.extend(fieldlist(types,target,seen));at+=8
        elif kind==0x1502:
            _,end=numeric(data,at+4);_,at=cstring(data,end)
        else:raise ValueError('Unsupported field-list leaf '+hex(kind))
    return out


def inspect(pdb,exe,out,queries=()):
    msf=Msf(pdb);pe=pefile.PE(str(exe));debug=[]
    for entry in getattr(pe,'DIRECTORY_ENTRY_DEBUG',[]):
        data=pe.get_data(entry.struct.AddressOfRawData,entry.struct.SizeOfData)
        if data[:4]==b'RSDS':debug.append((str(uuid.UUID(bytes_le=data[4:20])),struct.unpack_from('<I',data,20)[0]))
    if (msf.guid,msf.age) not in debug:raise ValueError('PDB GUID/age does not match executable')
    dbi=msf.streams[3];symbol_stream=struct.unpack_from('<H',dbi,20)[0]
    sizes=struct.unpack_from('<6I',dbi,24)
    # The optional debug header follows module/section/file/type-server and EC data.
    optional_at=64+sum(sizes[i] for i in (0,1,2,3,4))+struct.unpack_from('<I',dbi,52)[0]
    optional_size=struct.unpack_from('<I',dbi,48)[0]
    optional=struct.unpack_from('<'+str(optional_size//2)+'H',dbi,optional_at) if optional_size else ()
    has_omap=any(i<len(optional) and optional[i]!=0xffff for i in (3,4))
    publics=[];symbol_kinds=collections.Counter()
    for _,kind,rec in records(msf.streams[symbol_stream]):
        symbol_kinds[hex(kind)]+=1
        if kind!=0x110e:continue
        flags,offset,segment=struct.unpack_from('<IIH',rec,4);name,_=cstring(rec,14)
        row=dict(name=name,segment=segment,offset=offset,flags=flags)
        if not has_omap and 0<segment<=len(pe.sections):
            section=pe.sections[segment-1]
            if offset<max(section.Misc_VirtualSize,section.SizeOfRawData):
                row['rva']=section.VirtualAddress+offset;row['section']=section.Name.rstrip(b'\0').decode(errors='replace')
        publics.append(row)
    tpi=msf.streams[2];_,header,begin,end,nbytes=struct.unpack_from('<5I',tpi)
    tags=[];type_kinds=collections.Counter();type_records={}
    for index,(_,kind,rec) in enumerate(records(tpi,header,header+nbytes),begin):
        type_kinds[hex(kind)]+=1;type_records[index]=(kind,rec)
        if kind in (0x1504,0x1505,0x1506):
            count,options,fieldlist_index=struct.unpack_from('<HHI',rec,4)
            size,at=numeric(rec,12 if kind==0x1506 else 20);name,_=cstring(rec,at)
            tags.append(dict(index=index,name=name,size=size,forward=bool(options&0x80),fieldlist=fieldlist_index,members=count,kind=hex(kind)))
    if len(type_records)!=end-begin:raise ValueError('TPI type index count mismatch')
    tag_names={r['index']:r['name'] for r in tags}
    primitives={0x40:'float',0x41:'double',0x74:'int',0x75:'unsigned int',0x70:'char',0x20:'unsigned char',
                0x10:'signed char',0x71:'wchar_t',0x11:'short',0x21:'unsigned short',0x30:'bool',0x03:'void'}
    def type_name(index,depth=0):
        if depth>6:return hex(index)
        if index in tag_names:return tag_names[index]
        if index in primitives:return primitives[index]
        kind,data=type_records.get(index,(None,None))
        if kind in (0x1001,0x1002):
            child=struct.unpack_from('<I',data,4)[0]
            return type_name(child,depth+1)+('*' if kind==0x1002 else ' [modifier]')
        return hex(index)
    selected=[]
    for tag in tags:
        if tag['forward'] or not any(q.casefold() in tag['name'].casefold() for q in queries):continue
        row=dict(tag)
        try:
            row['fields']=fieldlist(type_records,tag['fieldlist'])
            for member in row['fields']:member['type_name']=type_name(member['type_index'])
            row['fields_complete']=True
        except ValueError as e:row['fields_complete']=False;row['diagnostic']=str(e)
        selected.append(row)
    mod_size,contrib_size,map_size,file_size=struct.unpack_from('<4I',dbi,24)
    fileinfo=dbi[64+mod_size+contrib_size+map_size:64+mod_size+contrib_size+map_size+file_size]
    source_files=[]
    if fileinfo:
        modules,_=struct.unpack_from('<HH',fileinfo)
        counts=struct.unpack_from('<'+str(modules)+'H',fileinfo,4+2*modules)
        nfiles=sum(counts);offsets=struct.unpack_from('<'+str(nfiles)+'I',fileinfo,4+4*modules)
        names=4+4*modules+4*nfiles
        source_files=sorted({cstring(fileinfo,names+off)[0] for off in offsets})
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    for filename,data in [('publics.json',publics),('types.json',tags),('source-files.json',source_files),('selected-fields.json',selected)]:
        (out/filename).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    summary=dict(pdb=str(pathlib.Path(pdb).resolve()),exe=str(pathlib.Path(exe).resolve()),guid=msf.guid,age=msf.age,
        matched=True,pdb_sha256=hashlib.sha256(msf.raw).hexdigest(),publics=len(publics),function_publics=sum(bool(r['flags']&2) for r in publics),
        mapped_public_rvas=sum('rva' in r for r in publics),omap_present=has_omap,type_records=len(type_records),tag_records=len(tags),
        complete_tags=sum(not r['forward'] for r in tags),source_files=len(source_files),symbol_kinds=dict(symbol_kinds),type_kinds=dict(type_kinds))
    (out/'pdb-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdb',type=pathlib.Path);parser.add_argument('exe',type=pathlib.Path);parser.add_argument('--out',type=pathlib.Path,required=True)
    parser.add_argument('--query',action='append',default=[])
    args=parser.parse_args();inspect(args.pdb,args.exe,args.out,args.query)
