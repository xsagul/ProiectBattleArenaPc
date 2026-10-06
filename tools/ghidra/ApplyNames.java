// Puts what we know into the Ghidra program before analysis: a function at every start of client-src/functions.txt,
// our names for packet classes / handlers / imports / hand-found functions (client-src/names.tsv, made by
// tools/ghidra_names.py). Run as a pre-script of analyzeHeadless with the names file as its argument.
//@category BattleArena
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

import java.io.BufferedReader;
import java.io.FileReader;

public class ApplyNames extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String path = getScriptArgs().length > 0 ? getScriptArgs()[0] : "client-src/names.tsv";
        long base = currentProgram.getImageBase().getOffset();
        int funcs = 0, named = 0, labels = 0, failed = 0;
        try (BufferedReader r = new BufferedReader(new FileReader(path))) {
            String line;
            while ((line = r.readLine()) != null) {
                String[] p = line.split("\t", -1);
                if (p.length < 3) continue;
                Address a = toAddr(base + Long.parseLong(p[0], 16));
                try {
                    if (p[1].equals("func")) {
                        Function f = getFunctionAt(a);
                        if (f == null) {
                            disassemble(a);
                            f = createFunction(a, null);
                            if (f != null) funcs++;
                        }
                        if (f != null && !p[2].isEmpty()) {
                            f.setName(p[2], SourceType.USER_DEFINED);
                            named++;
                        }
                    } else if (!p[2].isEmpty()) {
                        createLabel(a, p[2], true, SourceType.USER_DEFINED);
                        labels++;
                    }
                } catch (Exception e) {
                    failed++;
                }
            }
        }
        println("ApplyNames: functions created " + funcs + ", named " + named + ", labels " + labels + ", failed " + failed);
    }
}
