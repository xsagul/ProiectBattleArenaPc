// Decompiles every function of the program into readable pseudo-C, grouped by address (one file per 64 KiB of code:
// client-src/decomp/text_<rva>.c), and writes an index (client-src/decomp/index.tsv: rva, name, file, callers, size).
// Not compilable: it is for reading the client's code with our names instead of raw disassembly.
// Argument: the output directory. Optional second argument: only functions whose name contains this text.
//@category BattleArena
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.HashMap;
import java.util.Map;

public class ExportDecomp extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String out = getScriptArgs().length > 0 ? getScriptArgs()[0] : "client-src/decomp";
        String only = getScriptArgs().length > 1 ? getScriptArgs()[1] : null;
        new File(out).mkdirs();
        DecompInterface d = new DecompInterface();
        d.setOptions(new DecompileOptions());
        d.openProgram(currentProgram);
        long base = currentProgram.getImageBase().getOffset();
        Map<String, PrintWriter> files = new HashMap<>();
        PrintWriter index = new PrintWriter(new FileWriter(new File(out, only == null ? "index.tsv" : "index_partial.tsv")));
        index.println("# rva\tname\tfile\tcallers\tbytes");
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        int n = 0, bad = 0;
        while (it.hasNext() && !monitor.isCancelled()) {
            Function f = it.next();
            if (only != null && !f.getName().contains(only)) continue;
            long rva = f.getEntryPoint().getOffset() - base;
            String file = String.format("text_%06x.c", rva & ~0xffffL);
            PrintWriter w = files.get(file);
            if (w == null) {
                w = new PrintWriter(new FileWriter(new File(out, file), true));
                files.put(file, w);
            }
            DecompileResults res = d.decompileFunction(f, 60, monitor);
            String c = res != null && res.getDecompiledFunction() != null ? res.getDecompiledFunction().getC() : null;
            w.printf("// ---- rva 0x%x  %s  (%d callers)%n", rva, f.getName(), f.getCallingFunctions(monitor).size());
            if (c == null) {
                w.println("// (the decompiler failed: " + (res != null ? res.getErrorMessage() : "?") + ")");
                bad++;
            } else {
                w.println(c);
            }
            index.printf("%x\t%s\t%s\t%d\t%d%n", rva, f.getName(), file, f.getCallingFunctions(monitor).size(), f.getBody().getNumAddresses());
            n++;
            if (n % 2000 == 0) println("ExportDecomp: " + n + " functions");
        }
        for (PrintWriter w : files.values()) w.close();
        index.close();
        d.dispose();
        println("ExportDecomp: " + n + " functions, " + bad + " failed, " + files.size() + " files");
    }
}
