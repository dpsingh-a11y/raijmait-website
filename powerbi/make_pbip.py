"""Generates the Power BI Project (PBIP) for the Sai Trust dashboard.

    python3 make_pbip.py            -> writes ./SaiTrust/ (SaiTrust.pbip + SemanticModel + Report)

The semantic model (TMDL) re-uses the Power Query blocks from 01_PowerQuery_Import.m and the
measures from 02_DAX_Measures.dax, so those two files stay the single source of truth.
"""
import json, re, uuid, shutil, pathlib, textwrap

HERE = pathlib.Path(__file__).parent
OUT = HERE / "SaiTrust"
SM = OUT / "SaiTrust.SemanticModel"
RP = OUT / "SaiTrust.Report"
NS = uuid.UUID("5a17a0c0-0000-4000-8000-000000000001")
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
DEFAULT_PATH = r"C:\SaiTrust\Sai_Trust_Data.xlsx"

# ---------------------------------------------------------------- columns
# type codes: s string, d date, i int, n double, c currency(decimal), b boolean
T = dict(s="string", d="dateTime", i="int64", n="double", c="decimal", b="boolean")
def cols(spec):
    out = []
    for item in spec.split():
        name, t = item.split(":")
        out.append((name, t))
    return out

TABLES = {
 "Dim_Project": cols("Project_ID:s Project_Name:s Project_Code:s Start_Date:d End_Date:d Funding_Agency:s Active:b"),
 "Dim_SHG": cols("SHG_ID:s SHG_Name:s SHG_Code:s Location_ID:s State_ID:s District_ID:s Block_ID:s Project_ID:s Assigned_User_ID:s Village:s Formation_Date:d Bank_Name:s IFSC:s President_ID:s Secretary_ID:s Treasurer_ID:s Status:s State:s District:s Block:s Field_Officer:s SHG_Label:s"),
 "Dim_Member": cols("Member_ID:s SHG_ID:s Member_Name:s Gender:s DOB:d Mobile:s Joining_Date:d Exit_Date:d Status:s Age:i Age_Group:s Member_Label:s"),
 "Dim_FundSource": cols("Fund_Source_ID:s Source_Type:s Source_Name:s Organisation_Type:s Active:b"),
 "Dim_LoanPurpose": cols("Purpose_ID:s Purpose:s"),
 "Dim_ExpenseCategory": cols("Expense_Category_ID:s Expense_Category:s"),
 "Fact_Savings": cols("Savings_ID:s Date:d Member_ID:s Savings_Type:s Amount:c Payment_Mode:s Financial_Year:s Meeting_No:i Entered_By:s"),
 "Fact_Withdrawals": cols("Withdrawal_ID:s Date:d Member_ID:s Amount:c Reason:s Payment_Mode:s Approved_By:s"),
 "Fact_FundReceipts": cols("Receipt_ID:s Receipt_Date:d SHG_ID:s Fund_Source_ID:s Fund_Type:s Amount:c Payment_Mode:s Purpose:s Entered_By:s"),
 "Fact_Loans": cols("Loan_ID:s Loan_Number:s Member_ID:s Loan_Date:d Purpose_ID:s Principal_Amount:c Interest_Rate:n Interest_Type:s Tenure:i Installment_Amount:c Installment_Frequency:s First_Due_Date:d Loan_Status:s Approved_By:s"),
 "Fact_LoanSchedule": cols("Schedule_ID:s Loan_ID:s Installment_No:i Due_Date:d Principal_Due:c Interest_Due:c Status:s Installment_Due:c Member_ID:s Schedule_Bucket:s"),
 "Fact_Repayments": cols("Repayment_ID:s Loan_ID:s Member_ID:s Payment_Date:d Principal_Paid:c Interest_Paid:c Penalty:c Total_Paid:c Payment_Mode:s Receipt_No:s Entered_By:s"),
 "Fact_LoanApplications": cols("Application_ID:s Member_ID:s Application_Date:d Requested_Amount:c Purpose:s Tenure:i Status:s Approved_Amount:c Approval_Date:d"),
 "Fact_Expenses": cols("Expense_ID:s SHG_ID:s Expense_Date:d Expense_Category_ID:s Amount:c Payment_Mode:s Purpose:s Voucher_No:s"),
 "Fact_Meetings": cols("Meeting_ID:s SHG_ID:s Meeting_Date:d Meeting_No:i Facilitator:s Total_Members:i Members_Present:i Agenda:s"),
 "Fact_Agriculture": cols("Member_ID:s Has_Land:s Land_Unit:s Own_Land_Ha:n Agri_Land_Ha:n Irrigated_Land_Ha:n Leased_Land_Ha:n Total_Land_Ha:n Farm_Equipment:s Cultivated:s Crop:s Season:s Sowing_Date:d Sown_Area_Ha:n Seed_Qty_Kg:n Validation_Status:s Seed_Type:s Seed_Source:s Fertilizer:s Insect_Control:s Weed_Management:s Irrigation_Source:s Irrigation_Method:s Practice_Adopted:s Input_Support:s Input_Support_Type:s Demo_Plot:s Training:s Training_Type:s Exposure:s Exposure_Type:s Production_Qtl:n Income:c Cultivation_Cost:c Net_Profit:c LY_Crop:s LY_Area_Ha:n LY_Production_Qtl:n LY_Income:c LY_Cost:c LY_Profit:c Submit_Date:d Record_ID:i"),
}
# columns that are keys / ids: never summarised
def summarize(name, t):
    if t in "sdb": return "none"
    if name.endswith("_ID") or name in ("Age", "Tenure", "Meeting_No", "Installment_No", "Record_ID"): return "none"
    return "sum"
FMT = {"c": '"₹"#,0', "d": "dd-mmm-yyyy", "n": "#,0.00", "i": "0"}

# ---------------------------------------------------------------- helpers
def q(name):
    return name if re.fullmatch(r"\w+", name) else "'" + name.replace("'", "''") + "'"
def ind(text, n):
    pad = "\t" * n
    return "\n".join((pad + l) if l.strip() else "" for l in text.split("\n"))
def guid(key): return str(uuid.uuid5(NS, key))
def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
def wjson(path, obj): write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------- parse the M file
m_text = (HERE / "01_PowerQuery_Import.m").read_text(encoding="utf-8")
blocks = {}
for hdr in re.finditer(r"^// (B\d+|BLOCK A)\s+[–-]\s+query name:\s+(\w+)\s*$", m_text, re.M):
    start = hdr.end()
    body = re.search(r"^(let\b|\(SheetName)", m_text[start:], re.M)
    s = start + body.start()
    end = re.search(r"^// -{20,}|^// ={20,}", m_text[s:], re.M)
    blocks[hdr.group(2)] = m_text[s: s + end.start() if end else None].strip("\n")
FN = blocks.pop("fnSheet")
missing = set(TABLES) - set(blocks)
assert not missing, missing

# ---------------------------------------------------------------- parse the DAX file
dax = (HERE / "02_DAX_Measures.dax").read_text(encoding="utf-8").split("\n")
start = next(i for i, l in enumerate(dax) if l.startswith("// 3. MEMBERS"))
measures, folder = [], "General"
i = start
hdr_re = re.compile(r"^([A-Za-z][^=\n]*?)\s+=\s*(.*)$")
while i < len(dax):
    l = dax[i]
    m = re.search(r"\[folder:\s*\d*\s*([^\]]+)\]", l)
    if m: folder = m.group(1).strip()
    if l.startswith("// 9. DISPLAY HELPERS"): folder = "Helpers"
    if l.startswith("//") or not l.strip():
        i += 1; continue
    h = hdr_re.match(l)
    if not h: i += 1; continue
    name, expr = h.group(1).strip(), h.group(2)
    if expr.strip():
        expr = re.sub(r"\s+//.*$", "", expr).strip()
        measures.append([name, expr, folder]); i += 1
    else:
        body = []; i += 1
        depth = 0
        while i < len(dax) and dax[i].strip():
            nxt = hdr_re.match(dax[i])
            if nxt and body and depth <= 0 and not re.match(r"(VAR|RETURN)\b", dax[i]) and not dax[i][0].isspace():
                break                                   # next measure starts right after a balanced body
            if not dax[i].lstrip().startswith("//"):
                line = re.sub(r"\s+//.*$", "", dax[i]).rstrip()
                body.append(line)
                depth += line.count("(") - line.count(")")
            i += 1
        measures.append([name, "\n".join(body), folder])
names = [m[0] for m in measures]
assert len(names) == len(set(names)), [n for n in names if names.count(n) > 1]

def mfmt(name):
    if "%" in name: return "0.0%"
    if name.endswith("#") or name in ("SHG Count", "Active SHGs", "Members", "Female Members", "Villages Covered", "Districts Covered",
            "Savers", "Borrowers", "Meetings Held", "Survey Records", "Farmers Surveyed", "Cultivating Records", "Applications #",
            "Loan Overdue Instalments"): return "#,0"
    if re.search(r"Per Member|per Member|Savings per|Fund per|Expense per|Avg Loan|Avg Saving|Avg Profit|per ha|per Record", name) and "Profit" not in name: return '"₹"#,0'
    if re.search(r"Ratio|Yield|Rate|Age|Members per|Meetings per|Tenure|Avg Land|Holding|Area|Production", name): return "#,0.00"
    if re.search(r"Savings|Withdrawals|Fund|Expenses|Disbursed|Collected|Outstanding|Overdue|Due|Cash|Income|Cost|Profit|Amount|Principal|Instalments|Repaid", name):
        if name in ("PAR Colour", "Repayment Colour", "PAR Status", "Selected Filters Text", "Rs Short (Savings)"): return None
        return '"₹"#,0'
    return None

# ---------------------------------------------------------------- semantic model
def table_tmdl(name, columns):
    L = [f"table {q(name)}", ""]
    for cname, t in columns:
        L.append(f"\tcolumn {q(cname)}")
        L.append(f"\t\tdataType: {T[t]}")
        if t in FMT and not cname.endswith("_ID"): L.append(f"\t\tformatString: {FMT[t]}")
        L.append(f"\t\tsummarizeBy: {summarize(cname, t)}")
        L.append(f"\t\tsourceColumn: {cname}")
        L.append("")
    L.append(f"\tpartition {q(name)} = m")
    L.append("\t\tmode: import")
    L.append("\t\tsource =")
    L.append(ind(blocks[name], 3))
    L.append("")
    return "\n".join(L)

DATE_COLS = [("Date", "dateTime", None), ("Year", "int64", None), ("Month No", "int64", None), ("Month", "string", "Month No"),
             ("Month Year", "string", "Month Year Sort"), ("Month Year Sort", "int64", None), ("Quarter", "string", None),
             ("Financial Year", "string", None), ("Day Name", "string", None)]
dim_date_expr = re.search(r"^Dim_Date =\n(.*?)\n// then:", "\n".join(dax), re.S | re.M).group(1)

def date_tmdl():
    L = ["table Dim_Date", "\tdataCategory: Time", ""]
    for n, t, sort in DATE_COLS:
        L.append(f"\tcolumn {q(n)}")
        L.append(f"\t\tdataType: {t}")
        if n == "Date": L += ["\t\tisKey", "\t\tformatString: dd-mmm-yyyy"]
        L.append("\t\tsummarizeBy: none")
        L.append(f"\t\tsourceColumn: [{n}]")
        if sort: L.append(f"\t\tsortByColumn: {q(sort)}")
        L.append("")
    L += ["\tpartition Dim_Date = calculated", "\t\tmode: import", "\t\tsource =", ind(dim_date_expr, 3), ""]
    return "\n".join(L)

def measures_tmdl():
    L = ["table _Measures", "", "\tcolumn x", "\t\tdataType: int64", "\t\tisHidden", "\t\tsummarizeBy: none", "\t\tsourceColumn: [x]", ""]
    for name, expr, folder in measures:
        lines = expr.split("\n")
        if len(lines) == 1:
            L.append(f"\tmeasure {q(name)} = {expr}")
        else:
            L.append(f"\tmeasure {q(name)} =")
            L.append(ind(textwrap.dedent("\n".join(lines)), 3))
        f = mfmt(name)
        if f: L.append(f"\t\tformatString: {f}")
        L.append(f"\t\tdisplayFolder: {q(folder) if ' ' in folder else folder}")
        L.append("")
    L += ["\tpartition _Measures = calculated", "\t\tmode: import", "\t\tsource = ROW ( \"x\", 1 )", ""]
    return "\n".join(L)

REL = [  # (many side, one side)
 ("Dim_SHG.Project_ID", "Dim_Project.Project_ID"),
 ("Dim_Member.SHG_ID", "Dim_SHG.SHG_ID"),
 ("Fact_FundReceipts.SHG_ID", "Dim_SHG.SHG_ID"), ("Fact_Expenses.SHG_ID", "Dim_SHG.SHG_ID"), ("Fact_Meetings.SHG_ID", "Dim_SHG.SHG_ID"),
 ("Fact_Savings.Member_ID", "Dim_Member.Member_ID"), ("Fact_Withdrawals.Member_ID", "Dim_Member.Member_ID"),
 ("Fact_Loans.Member_ID", "Dim_Member.Member_ID"), ("Fact_LoanSchedule.Member_ID", "Dim_Member.Member_ID"),
 ("Fact_Repayments.Member_ID", "Dim_Member.Member_ID"), ("Fact_LoanApplications.Member_ID", "Dim_Member.Member_ID"),
 ("Fact_Agriculture.Member_ID", "Dim_Member.Member_ID"),
 ("Fact_FundReceipts.Fund_Source_ID", "Dim_FundSource.Fund_Source_ID"),
 ("Fact_Loans.Purpose_ID", "Dim_LoanPurpose.Purpose_ID"),
 ("Fact_Expenses.Expense_Category_ID", "Dim_ExpenseCategory.Expense_Category_ID"),
] + [(f"{t}.{c}", "Dim_Date.Date") for t, c in [
 ("Fact_Savings", "Date"), ("Fact_Withdrawals", "Date"), ("Fact_FundReceipts", "Receipt_Date"), ("Fact_Loans", "Loan_Date"),
 ("Fact_Repayments", "Payment_Date"), ("Fact_Expenses", "Expense_Date"), ("Fact_Meetings", "Meeting_Date"),
 ("Fact_LoanSchedule", "Due_Date"), ("Fact_LoanApplications", "Application_Date"), ("Fact_Agriculture", "Submit_Date")]]

def build_model():
    d = SM / "definition"
    wjson(SM / "definition.pbism", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json", "version": "4.0", "settings": {}})
    write(d / "database.tmdl", "database SaiTrust\n\tcompatibilityLevel: 1600\n")
    order = list(TABLES) + ["Dim_Date", "_Measures"]
    write(d / "model.tmdl", "model Model\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\n" + "\n".join(f"ref table {q(t)}" for t in order) + "\n\nref expression pFilePath\nref expression fnSheet\n")
    write(d / "expressions.tmdl",
          f'expression pFilePath = "{DEFAULT_PATH}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
          "\tlineageTag: " + guid("pFilePath") + "\n\n"
          "expression fnSheet =\n" + ind(FN, 2) + "\n\tlineageTag: " + guid("fnSheet") + "\n")
    for t, c in TABLES.items(): write(d / "tables" / f"{t}.tmdl", table_tmdl(t, c))
    write(d / "tables" / "Dim_Date.tmdl", date_tmdl())
    write(d / "tables" / "_Measures.tmdl", measures_tmdl())
    rel = []
    for many, one in REL:
        rel += [f"relationship {guid(many + one)}", f"\tfromColumn: {many}", f"\ttoColumn: {one}", ""]
    write(d / "relationships.tmdl", "\n".join(rel))

# ---------------------------------------------------------------- report
def lit(v):
    if isinstance(v, bool): return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)): return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}

def col(t, p): return ("Column", t, p)
def mea(n): return ("Measure", "_Measures", n)
def field(f):
    kind, t, p = f
    return {kind: {"Expression": {"SourceRef": {"Entity": t}}, "Property": p}}
def proj(f):
    return {"field": field(f), "queryRef": f"{f[1]}.{f[2]}", "nativeQueryRef": f[2]}

W, GAP, MARGIN = 1280, 8, 16
def title_obj(text):
    return {"title": [{"properties": {"show": lit(True), "text": lit(text), "fontSize": lit(12), "bold": lit(True)}}]}

def visual(vtype, name, x, y, w, h, roles=None, title=None, objects=None, sort=None, sync=None, container=None):
    v = {"visualType": vtype}
    if roles:
        qs = {"queryState": {r: {"projections": [proj(f) for f in fs]} for r, fs in roles.items()}}
        if sort: qs["sortDefinition"] = {"sort": [{"field": field(sort[0]), "direction": sort[1]}], "isDefaultSort": True}
        v["query"] = qs
    if objects: v["objects"] = objects
    co = dict(container or {})
    if title: co.update(title_obj(title))
    elif vtype in ("card", "slicer"): co["title"] = [{"properties": {"show": lit(False)}}]
    if co: v["visualContainerObjects"] = co
    if sync: v["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
    v["drillFilterOtherVisuals"] = True
    return {"$schema": f"{SCHEMA}/visualContainer/2.1.0/schema.json", "name": name,
            "position": {"x": x, "y": y, "z": 0, "width": w, "height": h, "tabOrder": 0}, "visual": v}

FILTERS = [("Project", col("Dim_Project", "Project_Name")), ("State", col("Dim_SHG", "State")), ("District", col("Dim_SHG", "District")),
           ("SHG", col("Dim_SHG", "SHG_Label")), ("FY", col("Dim_Date", "Financial Year"))]

class Page:
    def __init__(self, key, title):
        self.key, self.title, self.visuals, self.y, self.n = key, title, [], 0, 0
        self._chrome()
    def vid(self): self.n += 1; return f"{self.key}{self.n:02d}"
    def _chrome(self):
        sw = (W - 2 * MARGIN - 4 * GAP) / 5
        for k, (label, f) in enumerate(FILTERS):
            self.visuals.append(visual("slicer", self.vid(), MARGIN + k * (sw + GAP), 10, sw, 44, {"Values": [f]}, sync=label,
                objects={"data": [{"properties": {"mode": lit("Dropdown")}}], "header": [{"properties": {"show": lit(True), "text": lit(label)}}]}))
        self.visuals.append(visual("pageNavigator", self.vid(), MARGIN, 62, W - 2 * MARGIN, 40,
            objects={"general": [{"properties": {"orientation": lit("Horizontal")}}]}))
        self.y = 112
    def cards(self, ms, labels=None):
        n = len(ms); w = (W - 2 * MARGIN - (n - 1) * GAP) / n
        for k, m in enumerate(ms):
            self.visuals.append(visual("card", self.vid(), MARGIN + k * (w + GAP), self.y, w, 84, {"Values": [mea(m)]}))
        self.y += 84 + GAP
    def row(self, items, h=290):
        """items: list of (visualType, title, roles, sort) with equal share of the width."""
        n = len(items); w = (W - 2 * MARGIN - (n - 1) * GAP) / n
        for k, it in enumerate(items):
            vt, title, roles = it[0], it[1], it[2]
            sort = it[3] if len(it) > 3 else None
            self.visuals.append(visual(vt, self.vid(), MARGIN + k * (w + GAP), self.y, w, h, roles, title=title, sort=sort))
        self.y += h + GAP
    def text(self, paras, h=520):
        runs = [{"paragraphs": [{"textRuns": [{"value": p[0], "textStyle": ({"fontWeight": "bold"} if p[1] else {})}]} for p in paras]}]
        v = {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": runs[0]["paragraphs"]}}]}, "drillFilterOtherVisuals": True}
        self.visuals.append({"$schema": f"{SCHEMA}/visualContainer/2.1.0/schema.json", "name": self.vid(),
            "position": {"x": MARGIN, "y": self.y, "z": 0, "width": 900, "height": h, "tabOrder": 0}, "visual": v})
        self.y += h + GAP

BAR, COL, LINE, STACK, TABLE = "clusteredBarChart", "clusteredColumnChart", "lineChart", "columnChart", "tableEx"
def cat(c, *ms, series=None):
    r = {"Category": [c], "Y": [mea(m) for m in ms]}
    if series: r["Series"] = [series]
    return r
D = lambda p: col("Dim_Date", p)
desc = lambda m: (mea(m), "Descending")

def build_pages():
    P = []
    p = Page("ov", "Overview")
    p.cards(["SHG Count", "Net Savings", "Fund Received", "Loans Disbursed", "Outstanding Principal", "Repayment Rate %", "PAR %", "Estimated Cash Balance"])
    p.row([(LINE, "Monthly money flow", cat(D("Month Year"), "Total Savings", "Loans Disbursed", "Total Collected"))], 300)
    p.row([(BAR, "Funds received by type", cat(col("Fact_FundReceipts", "Fund_Type"), "Fund Received"), desc("Fund Received")),
           (BAR, "Loans by purpose", cat(col("Dim_LoanPurpose", "Purpose"), "Loans Disbursed"), desc("Loans Disbursed")),
           (BAR, "SHGs by district", cat(col("Dim_SHG", "District"), "SHG Count"), desc("SHG Count"))])
    p.row([(BAR, "Funds received by project", cat(col("Dim_Project", "Project_Name"), "Fund Received"), desc("Fund Received"))], 300)
    P.append(p)

    p = Page("sv", "Savings & Funds")
    p.cards(["Total Savings", "Total Withdrawals", "Net Savings", "Savings per Member", "Fund Received", "Total Expenses", "Expense % of Funds"])
    p.row([(COL, "Savings and withdrawals by month", cat(D("Month Year"), "Total Savings", "Total Withdrawals"))], 300)
    p.row([(BAR, "Net savings by SHG", cat(col("Dim_SHG", "SHG_Label"), "Net Savings"), desc("Net Savings")),
           (BAR, "Withdrawals by reason", cat(col("Fact_Withdrawals", "Reason"), "Total Withdrawals"), desc("Total Withdrawals"))], 340)
    p.row([(BAR, "Funds by source", cat(col("Dim_FundSource", "Source_Name"), "Fund Received"), desc("Fund Received")),
           (BAR, "Expenses by category", cat(col("Dim_ExpenseCategory", "Expense_Category"), "Total Expenses"), desc("Total Expenses"))], 340)
    p.row([(TABLE, "Fund receipts", {"Values": [col("Fact_FundReceipts", "Receipt_Date"), col("Dim_SHG", "SHG_Label"), col("Dim_FundSource", "Source_Name"),
            col("Fact_FundReceipts", "Fund_Type"), col("Fact_FundReceipts", "Payment_Mode"), mea("Fund Received")]})], 300)
    P.append(p)

    p = Page("ln", "Loans")
    p.cards(["Loans Disbursed", "Outstanding Principal", "Total Collected", "Repayment Rate %", "PAR %", "Avg Loan Size", "Upcoming Due (30 days)", "Approval Rate %"])
    p.row([(STACK, "Instalments by due month", cat(D("Month Year"), "Scheduled Instalments", series=col("Fact_LoanSchedule", "Schedule_Bucket")))], 300)
    p.row([(BAR, "Outstanding principal by SHG", cat(col("Dim_SHG", "SHG_Label"), "Outstanding Principal"), desc("Outstanding Principal")),
           (COL, "Loan applications by status", cat(col("Fact_LoanApplications", "Status"), "Applied Amount", "Approved Amount")),
           (BAR, "Loans by purpose", cat(col("Dim_LoanPurpose", "Purpose"), "Loans Disbursed"), desc("Loans Disbursed"))], 340)
    p.row([(TABLE, "Loan register", {"Values": [col("Fact_Loans", "Loan_ID"), col("Dim_Member", "Member_Name"), col("Dim_SHG", "SHG_Label"), col("Dim_LoanPurpose", "Purpose"),
            col("Fact_Loans", "Principal_Amount"), mea("Loan Repaid"), mea("Loan Outstanding"), col("Fact_Loans", "Interest_Rate"), mea("Loan Overdue Instalments")]})], 380)
    P.append(p)

    p = Page("sh", "SHGs & Members")
    p.cards(["SHG Count", "Members", "Female %", "Avg Members per SHG", "Meetings Held", "Attendance %"])
    p.row([(BAR, "Members per SHG", cat(col("Dim_SHG", "SHG_Label"), "Members"), desc("Members")),
           (COL, "Members by age group", cat(col("Dim_Member", "Age_Group"), "Members")),
           (LINE, "SHGs formed over time", cat(col("Dim_SHG", "Formation_Date"), "SHG Count"))], 340)
    p.row([(BAR, "Meeting attendance by SHG", cat(col("Dim_SHG", "SHG_Label"), "Attendance %"), (mea("Attendance %"), "Ascending"))], 340)
    p.row([(TABLE, "SHG scorecard", {"Values": [col("Dim_SHG", "SHG_Label"), col("Dim_SHG", "District"), col("Dim_Project", "Project_Name"), mea("Members"), mea("Net Savings"),
            mea("Outstanding Principal"), mea("Overdue Principal"), mea("Attendance %")]})], 380)
    P.append(p)

    p = Page("ag", "Agriculture")
    p.cards(["Farmers Surveyed", "Area Sown (ha)", "Crop Income", "Net Profit", "Benefit Cost Ratio", "Yield (qtl/ha)", "Training Coverage %", "Irrigated % of Agri Land"])
    A = lambda c: col("Fact_Agriculture", c)
    p.row([(BAR, "Net profit by crop", cat(A("Crop"), "Net Profit"), desc("Net Profit"))], 380)
    p.row([(BAR, "Area sown by crop (ha)", cat(A("Crop"), "Area Sown (ha)"), desc("Area Sown (ha)")),
           (COL, "Net profit by season", cat(A("Season"), "Net Profit")),
           (BAR, "Programme reach", {"Y": [mea(m) for m in ["Training Coverage %", "Input Support %", "Exposure Visit %", "Demo Plot %", "Improved Practice %"]]})], 320)
    p.row([(COL, "Average profit per record: trained vs not", cat(A("Training"), "Avg Profit per Record")),
           (COL, "Profit this year vs last year", {"Y": [mea("Net Profit"), mea("Last Year Profit")]}),
           (BAR, "Irrigation source", cat(A("Irrigation_Source"), "Survey Records"), desc("Survey Records"))], 300)
    p.row([(BAR, "Irrigation method", cat(A("Irrigation_Method"), "Survey Records"), desc("Survey Records")),
           (BAR, "Practices adopted", cat(A("Practice_Adopted"), "Survey Records"), desc("Survey Records")),
           (BAR, "Seed source", cat(A("Seed_Source"), "Survey Records"), desc("Survey Records"))], 300)
    P.append(p)

    p = Page("nt", "Data notes")
    notes = [("What to know about this workbook", True),
     ("The README sheet says all names, accounts and transactions are fictional test data.", False),
     ("Dates do not line up: 46 of 125 savings entries and 7 of 19 loans are dated before the SHG was formed.", False),
     ("Attendance is unreliable: 17 of 20 meetings record 16 to 18 members, but the groups have 3 to 5 registered members.", False),
     ("4 withdrawals are larger than the member's recorded savings.", False),
     ("The SHGs sheet balance columns are empty or do not reconcile, so every balance here is calculated from transactions.", False),
     ("Agriculture has 100 survey records for 65 members. Land and last-year figures differ between a member's rows, so each row is treated as its own record.", False),
     ("Overdue means a pending instalment with a due date before today. Estimated Cash Balance has no opening balance.", False)]
    p.text(notes, 360)
    P.append(p)
    return P

def build_report():
    d = RP / "definition"
    wjson(RP / "definition.pbir", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
                                   "version": "4.0", "datasetReference": {"byPath": {"path": "../SaiTrust.SemanticModel"}}})
    wjson(d / "version.json", {"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    ver = {"visual": "2.1.0", "report": "3.1.0", "page": "2.1.0"}
    wjson(d / "report.json", {
        "$schema": f"{SCHEMA}/report/3.1.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": ver, "type": "SharedResources"},
                            "customTheme": {"name": "SaiTrust.json", "reportVersionAtImport": ver, "type": "RegisteredResources"}},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources", "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources", "items": [{"name": "SaiTrust.json", "path": "SaiTrust.json", "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "allowChangeFilterTypes": True, "useEnhancedTooltips": True}})
    (RP / "StaticResources" / "RegisteredResources").mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "03_Sai_Trust_Theme.json", RP / "StaticResources" / "RegisteredResources" / "SaiTrust.json")
    pages = build_pages()
    wjson(d / "pages" / "pages.json", {"$schema": f"{SCHEMA}/pagesMetadata/1.1.0/schema.json", "pageOrder": [p.key for p in pages], "activePageName": pages[0].key})
    for p in pages:
        wjson(d / "pages" / p.key / "page.json", {"$schema": f"{SCHEMA}/page/2.1.0/schema.json", "name": p.key, "displayName": p.title,
                                                  "displayOption": "FitToWidth", "height": int(p.y + 20), "width": W})
        for v in p.visuals:
            wjson(d / "pages" / p.key / "visuals" / v["name"] / "visual.json", v)

if __name__ == "__main__":
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    wjson(OUT / "SaiTrust.pbip", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0", "artifacts": [{"report": {"path": "SaiTrust.Report"}}], "settings": {"enableAutoRecovery": True}})
    build_model(); build_report()
    print("tables:", len(TABLES) + 2, "| measures:", len(measures), "| relationships:", len(REL), "| wrote", OUT)
