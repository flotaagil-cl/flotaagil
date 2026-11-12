from datamodel import E, REL
import subprocess
lines = ['digraph ER {', 'graph [rankdir=LR, splines=true, nodesep=0.25, ranksep=0.55, fontname="Carlito", pad=0.2];',
         'node [shape=plain, fontname="Carlito", fontsize=11];', 'edge [dir=both, color="#1b1f24", penwidth=0.9, arrowsize=0.8];']
for name, (desc, cols) in E.items():
    rows = []
    for c in cols:
        k = c[3]
        mark = ""
        if "PK" in k: mark = "PK"
        if "FK" in k: mark = (mark + " " if mark else "") + "FK"
        if k.startswith("UK") and not mark: mark = "UK"
        fname = f"<B>{c[0]}</B>" if "PK" in k else c[0]
        rows.append(f'<TR><TD ALIGN="LEFT" WIDTH="34">{"<FONT POINT-SIZE=\"9\" COLOR=\"#5a6472\">"+mark+"</FONT>" if mark else " "}</TD><TD ALIGN="LEFT">{fname}</TD><TD ALIGN="LEFT"><FONT POINT-SIZE="9" COLOR="#5a6472">{c[1].split("(")[0]}</FONT></TD></TR>')
    html = f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2" COLOR="#1b1f24"><TR><TD COLSPAN="3" BGCOLOR="#e9edf3"><B>{name}</B></TD></TR>{"".join(rows)}</TABLE>>'
    lines.append(f'{name} [label={html}];')
ends = {"1:1": ("teetee", "teetee"), "1:N": ("teetee", "crowodot"), "1:0..1": ("teetee", "teeodot"), "0..1:N": ("teeodot", "crowodot")}
for p, c, card in REL:
    a_p, a_c = ends[card]
    lines.append(f'{p} -> {c} [arrowtail={a_p}, arrowhead={a_c}];')
lines.append('}')
open('fig/er.dot', 'w').write("\n".join(lines))
subprocess.run(["dot", "-Tpng", "-Gdpi=200", "fig/er.dot", "-o", "fig/modelo_datos.png"], check=True)
