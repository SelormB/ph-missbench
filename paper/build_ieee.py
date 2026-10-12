#!/usr/bin/env python3
"""Build the IEEE two-column (IEEEtran journal) version of the preprint.

Source: paper/manuscript.md, written by build_manuscript.py from the pipeline outputs, so
every number stays tied to stats.json. This script only re-typesets that text: prose is
converted with pandoc, tables and figures are rebuilt as IEEE floats, citations become
BibTeX \\cite commands (IEEEtran.bst numbers them in order of first citation), and the
declarations move to the title footnote and the end-matter sections.

    python paper/build_manuscript.py --final
    python code/06_figures.py --final --ieee
    python paper/build_ieee.py            # writes paper/ieee/ and PH-MissBench_preprint_IEEE.pdf
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "ieee"
MD = (HERE / "manuscript.md").read_text()
AUTH = json.loads((ROOT / "AUTHORS.json").read_text())["authors"][0]

# ---------------------------------------------------------------- references
KEYS = ["jager2021", "jarrett2022", "perezlebel2022", "lemorvan2025", "josse2019", "rubin1976",
        "vanbuuren2011", "stekhoven2012", "ke2017", "saito2015", "vancalster2019", "nchs2024guide",
        "osterman2026"]
BIB = r"""
@article{jager2021,
  author  = {J{\"a}ger, Sebastian and Allhorn, Arndt and Bie{\ss}mann, Felix},
  title   = {A Benchmark for Data Imputation Methods},
  journal = {Frontiers in Big Data},
  volume  = {4},
  pages   = {693674},
  year    = {2021},
  doi     = {10.3389/fdata.2021.693674}
}
@inproceedings{jarrett2022,
  author    = {Jarrett, Daniel and Cebere, Bogdan C. and Liu, Tennison and Curth, Alicia and van der Schaar, Mihaela},
  title     = {{HyperImpute}: Generalized Iterative Imputation with Automatic Model Selection},
  booktitle = {Proceedings of the 39th International Conference on Machine Learning},
  series    = {Proceedings of Machine Learning Research},
  volume    = {162},
  pages     = {9916--9937},
  year      = {2022}
}
@article{perezlebel2022,
  author  = {Perez-Lebel, Alexandre and Varoquaux, Ga{\"e}l and Le Morvan, Marine and Josse, Julie and Poline, Jean-Baptiste},
  title   = {Benchmarking Missing-Values Approaches for Predictive Models on Health Databases},
  journal = {GigaScience},
  volume  = {11},
  pages   = {giac013},
  year    = {2022},
  doi     = {10.1093/gigascience/giac013}
}
@inproceedings{lemorvan2025,
  author    = {Le Morvan, Marine and Varoquaux, Ga{\"e}l},
  title     = {Imputation for Prediction: Beware of Diminishing Returns},
  booktitle = {International Conference on Learning Representations (ICLR)},
  year      = {2025},
  note      = {arXiv:2407.19804}
}
@misc{josse2019,
  author = {Josse, Julie and Chen, Jacob M. and Prost, Nicolas and Scornet, Erwan and Varoquaux, Ga{\"e}l},
  title  = {On the Consistency of Supervised Learning with Missing Values},
  year   = {2019},
  note   = {arXiv:1902.06931 [stat.ML]},
  doi    = {10.48550/arXiv.1902.06931}
}
@article{rubin1976,
  author  = {Rubin, Donald B.},
  title   = {Inference and Missing Data},
  journal = {Biometrika},
  volume  = {63},
  number  = {3},
  pages   = {581--592},
  year    = {1976}
}
@article{vanbuuren2011,
  author  = {van Buuren, Stef and Groothuis-Oudshoorn, Karin},
  title   = {{mice}: Multivariate Imputation by Chained Equations in {R}},
  journal = {Journal of Statistical Software},
  volume  = {45},
  number  = {3},
  pages   = {1--67},
  year    = {2011}
}
@article{stekhoven2012,
  author  = {Stekhoven, Daniel J. and B{\"u}hlmann, Peter},
  title   = {{MissForest}---Non-Parametric Missing Value Imputation for Mixed-Type Data},
  journal = {Bioinformatics},
  volume  = {28},
  number  = {1},
  pages   = {112--118},
  year    = {2012}
}
@inproceedings{ke2017,
  author    = {Ke, Guolin and Meng, Qi and Finley, Thomas and Wang, Taifeng and Chen, Wei and Ma, Weidong and Ye, Qiwei and Liu, Tie-Yan},
  title     = {{LightGBM}: A Highly Efficient Gradient Boosting Decision Tree},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {30},
  pages     = {3146--3154},
  year      = {2017}
}
@article{saito2015,
  author  = {Saito, Takaya and Rehmsmeier, Marc},
  title   = {The Precision-Recall Plot Is More Informative than the {ROC} Plot When Evaluating Binary Classifiers on Imbalanced Datasets},
  journal = {PLoS ONE},
  volume  = {10},
  number  = {3},
  pages   = {e0118432},
  year    = {2015}
}
@article{vancalster2019,
  author  = {Van Calster, Ben and McLernon, David J. and van Smeden, Maarten and Wynants, Laure and Steyerberg, Ewout W.},
  title   = {Calibration: The {A}chilles Heel of Predictive Analytics},
  journal = {BMC Medicine},
  volume  = {17},
  pages   = {230},
  year    = {2019}
}
@manual{nchs2024guide,
  author       = {{National Center for Health Statistics}},
  title        = {User Guide to the 2022, 2023 and 2024 Natality Public Use Files},
  organization = {National Center for Health Statistics},
  address      = {Hyattsville, MD, USA},
  note         = {Available at \url{https://www.cdc.gov/nchs/data_access/vitalstatsonline.htm}}
}
@article{osterman2026,
  author  = {Osterman, Michelle J. K. and Hamilton, Brady E. and Martin, Joyce A. and Driscoll, Anne K. and Valenzuela, Claudia P.},
  title   = {Births: Final Data for 2024},
  journal = {National Vital Statistics Reports},
  volume  = {75},
  number  = {2},
  year    = {2026},
  month   = jun
}
"""

# ---------------------------------------------------------------- helpers
LABELS = {"Table 1": r"Table~\ref{tab:cohort}", "Table 2": r"Table~\ref{tab:baselines}",
          "Appendix Table A1": r"Table~\ref{tab:predictors} in the Appendix",
          "Figure 1": r"Fig.~\ref{fig:missing}", "Figure 2": r"Fig.~\ref{fig:informative}",
          "Figure 3": r"Fig.~\ref{fig:baselines}"}
SMALL = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with", "vs"}


def title_case(s):
    words = s.split()
    return " ".join(w if (i and w.lower() in SMALL) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def cite_tokens(text):
    """[1, 2] -> XCITEjager2021ZjarrettX (alphanumeric, survives pandoc)."""
    def rep(m):
        nums = [int(x) for x in re.split(r",\s*", m.group(1))]
        return "XCITE" + "Z".join(KEYS[n - 1] for n in nums) + "X"
    return re.sub(r"\[(\d+(?:,\s*\d+)*)\]", rep, text)


def ref_tokens(text):
    for k, v in sorted(LABELS.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(k, "XREF" + str(list(LABELS).index(k)) + "X")
    return text


def to_latex(md):
    md = ref_tokens(cite_tokens(md))
    tex = subprocess.run(["pandoc", "-f", "markdown", "-t", "latex", "--wrap=none"], input=md,
                         capture_output=True, text=True, check=True).stdout
    tex = re.sub(r"XCITE([A-Za-z0-9Z]+?)X", lambda m: r"\cite{" + m.group(1).replace("Z", ",") + "}", tex)
    tex = re.sub(r"XREF(\d)X", lambda m: list(LABELS.values())[int(m.group(1))], tex)
    tex = tex.replace("\\tightlist\n", "")
    return tex.strip()


def esc(s):
    return (s.replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%")
            .replace("_", r"\_").replace("#", r"\#"))


def pipe_rows(block):
    rows = [ln.strip().strip("|").split("|") for ln in block.strip().splitlines() if ln.strip().startswith("|")]
    rows = [[c.strip() for c in r] for r in rows]
    return rows[0], [r for r in rows[2:]]


def cell(c):
    m = re.fullmatch(r"`(.+)`", c)
    return r"\texttt{" + esc(m.group(1)) + "}" if m else esc(c).replace("–", "--")


def table(label, caption, header, rows, align, star=False, size=r"\footnotesize", note=None):
    env = "table*" if star else "table"
    body = [r"\begin{" + env + "}[!t]", r"\centering", size,
            r"\caption{" + caption + "}", r"\label{" + label + "}",
            r"\begin{tabular}{" + align + "}", r"\toprule",
            " & ".join(r"\textbf{" + esc(h) + "}" for h in header) + r" \\", r"\midrule"]
    body += [" & ".join(cell(c) for c in r) + r" \\" for r in rows]
    body += [r"\bottomrule", r"\end{tabular}"]
    if note:
        body += [r"\par\vspace{2pt}\parbox{" + (r"\textwidth" if star else r"\columnwidth") + r"}{\scriptsize " + note + "}"]
    body += [r"\end{" + env + "}"]
    return "\n".join(body)


def figure(label, path, caption, star=False):
    env = "figure*" if star else "figure"
    width = r"\textwidth" if star else r"\columnwidth"
    return "\n".join([r"\begin{" + env + "}[!t]", r"\centering",
                      r"\includegraphics[width=" + width + "]{" + path + "}",
                      r"\caption{" + to_latex(caption) + "}", r"\label{" + label + "}", r"\end{" + env + "}"])


# ---------------------------------------------------------------- parse manuscript.md
title = re.search(r"^# (.+)$", MD, re.M).group(1)
keywords = re.search(r"\*\*Keywords:\*\* (.+)", MD).group(1)
abstract_md = MD.split("## Abstract", 1)[1].split("## 1. Introduction", 1)[0]
abstract = " ".join(re.sub(r"\*\*[A-Za-z]+\.\*\*\s*", "", p).strip() for p in abstract_md.strip().split("\n\n"))
body_md = MD.split("## 1. Introduction", 1)[1]
body_md = "## 1. Introduction" + body_md.split("## Declarations", 1)[0]
decl = MD.split("## Declarations", 1)[1].split("## References", 1)[0]
appendix_md = MD.split("## Appendix", 1)[1]


def grab(label):
    m = re.search(r"\*\*" + re.escape(label) + r"\*\*\s*(.+)", decl)
    return m.group(1).strip() if m else ""


funding, ethics = grab("Funding."), grab("Ethics.")
contrib, ai_use = grab("Author contributions (CRediT)."), grab("Use of AI assistance.")

# ---------------------------------------------------------------- body conversion
floats = {"tab1": None, "tab2": None}
cohort_block = re.search(r"\*\*Table 1\.\*\* (.+?)\n\n(\|.+?)\n\n", body_md, re.S)
_h, _r = pipe_rows(cohort_block.group(2))
_r = [[c.replace("Very low birthweight", "VLBW").replace("Early preterm", "EPTB").replace(" (analytic cohort)", "")
       for c in row] for row in _r]
floats["tab1"] = table("tab:cohort", cohort_block.group(1).rstrip("."), _h, _r, align="@{}lrrr@{}",
                       note="EPTB, early preterm birth; VLBW, very low birthweight. The singleton row is the analytic cohort.")
body_md = body_md.replace(cohort_block.group(0), "XFLOATtab1X\n\n")

base_block = re.search(r"::: \{\.keep\}\n\*\*Table 2\.\*\* (.+?)\n\n(\|.+?)\n\n(Slope and intercept.+?)\n:::\n(B1 complete-case.+?)\n\n",
                       body_md, re.S)
hdr, rows = pipe_rows(base_block.group(2))
note = to_latex(base_block.group(4)) + " " + to_latex(base_block.group(3).replace("`paper/baselines_standard.csv`", "the released results file"))
floats["tab2"] = table("tab:baselines", base_block.group(1).rstrip("."), hdr, rows, align="llccrr", star=True,
                       note=note)
body_md = body_md.replace(base_block.group(0), "XFLOATtab2X\n\n")

figmap = {"figures/fig1.png": ("fig:missing", "figures/ieee/fig1.pdf", False),
          "figures/fig2.png": ("fig:informative", "figures/ieee/fig2.pdf", False),
          "figures/fig3.png": ("fig:baselines", "figures/ieee/fig3.pdf", True)}
for i, m in enumerate(re.finditer(r"!\[\*\*Figure \d\.\*\* (.+?)\]\((figures/fig\d\.png)\)", body_md)):
    lab, path, star = figmap[m.group(2)]
    floats[f"fig{i}"] = figure(lab, "../" + path, m.group(1), star)
    body_md = body_md.replace(m.group(0), f"XFLOATfig{i}X")

out = []
for block in re.split(r"\n(?=#{2,3} )", body_md):
    head, _, text = block.partition("\n")
    level = head.count("#")
    name = re.sub(r"^#+\s*(?:[\d.]+\s+)?", "", head).strip()
    if name.lower().startswith("code and data"):
        out.append(r"\section*{Code and Data Availability}")
    else:
        out.append((r"\section{" if level == 2 else r"\subsection{") + title_case(name) + "}")
    # split on float placeholders, convert the prose between them
    for piece in re.split(r"(XFLOAT\w+?X)", text):
        if piece.startswith("XFLOAT"):
            out.append(floats[piece[6:-1]])
        elif piece.strip():
            tex = to_latex(piece)
            tex = re.sub(r"\\textbf\{(Limitations|Future work)\.\}", r"\\textit{\1.}", tex)
            out.append(tex)
body_tex = "\n\n".join(out)

hdr, rows = pipe_rows(appendix_md)
pred_table = table("tab:predictors", re.search(r"\*\*Table A1\.\*\* (.+)", appendix_md).group(1).rstrip("."),
                   ["Field", "Description", "Not stated (%)", "NCHS-imputed (%)", "Not applicable (%)"], rows,
                   align="llrrr", star=True, size=r"\scriptsize")

author_note = (f"{esc(AUTH['name'])} is a Ph.D. student in Applied Statistics and Research Methods, "
               f"University of Northern Colorado, Greeley, CO, USA (e-mail: {esc(AUTH['email'])}; "
               f"ORCID: {AUTH['orcid']}).")

tex = r"""\documentclass[journal]{IEEEtran}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath}
\usepackage{cite}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{url}
\usepackage[hidelinks]{hyperref}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\DeclareUnicodeCharacter{2212}{\ensuremath{-}}
\DeclareUnicodeCharacter{2265}{\ensuremath{\geq}}
\DeclareUnicodeCharacter{00D7}{\ensuremath{\times}}

\begin{document}

\title{""" + to_latex(title).replace("\n", " ") + r"""}

\author{""" + esc(AUTH["name"]) + r"""%
\thanks{""" + author_note + r"""}%
\thanks{""" + to_latex(funding) + r"""}}


\maketitle

\begin{abstract}
""" + to_latex(abstract) + r"""
\end{abstract}

\begin{IEEEkeywords}
""" + ", ".join(k.strip()[:1].upper() + k.strip()[1:] for k in keywords.split(";")) + r""".
\end{IEEEkeywords}

""" + body_tex + r"""

\section*{Ethics Statement}
""" + to_latex(ethics) + r"""

\section*{Author Contributions}
""" + to_latex(contrib) + r"""

\section*{Use of AI Assistance}
""" + to_latex(ai_use) + r"""

\bibliographystyle{IEEEtran}
\bibliography{refs}

\appendices
\section{Predictor Missingness}
""" + to_latex("Appendix Table A1 lists every predictor with the share of the 2024 analytic cohort in each missingness class.") + "\n\n" + pred_table + r"""

\end{document}
"""

OUT.mkdir(exist_ok=True)
(OUT / "PH-MissBench_IEEE.tex").write_text(tex)
(OUT / "refs.bib").write_text(BIB.strip() + "\n")
print("wrote paper/ieee/PH-MissBench_IEEE.tex and refs.bib")

if shutil.which("pdflatex") and shutil.which("bibtex"):
    run = lambda *c: subprocess.run(c, cwd=OUT, capture_output=True, text=True)
    run("pdflatex", "-interaction=nonstopmode", "PH-MissBench_IEEE.tex")
    run("bibtex", "PH-MissBench_IEEE")
    run("pdflatex", "-interaction=nonstopmode", "PH-MissBench_IEEE.tex")
    r = run("pdflatex", "-interaction=nonstopmode", "PH-MissBench_IEEE.tex")
    if (OUT / "PH-MissBench_IEEE.pdf").exists():
        shutil.copy(OUT / "PH-MissBench_IEEE.pdf", HERE / "PH-MissBench_preprint_IEEE.pdf")
        print("wrote paper/PH-MissBench_preprint_IEEE.pdf")
    else:
        print(r.stdout[-3000:])
