// FreeType 2.10.1 (default configuration, one source file per module), compiled by Riot as C: ftgzip.c, the functions of it that are in the client (tools/match_objs.py).
// flags: -O2 -Itools/third_party/freetype-2.10.1/include -DFT2_BUILD_LIBRARY
// match: c0a440 _FT_Gzip_Uncompress
// match: c0a530 _FT_Stream_OpenGzip
// match: c0a950 _ft_gzip_check_header
// match: c0aac0 _ft_gzip_file_done
// match: c0ab20 _ft_gzip_file_fill_output
// match: c0ac00 _ft_gzip_file_io
// match: c0ad00 _ft_gzip_file_skip_output
// match: c0aef0 _huft_build
// match: c0b390 _inflate
// match: c0b780 _inflateEnd
// match: c0b860 _inflateInit2_
// match: c0baa0 _inflateReset
// match: c0baf0 _inflate_blocks
// match: c0caa0 _inflate_blocks_reset
// match: c0cb20 _inflate_codes
// match: c0d150 _inflate_flush
#include "../../../../tools/third_party/freetype-2.10.1/src/gzip/ftgzip.c"
