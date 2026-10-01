// =====================================================================
//  SAI TRUST – SHG FINANCE & LIVELIHOOD DASHBOARD
//  Power Query (M) – import every sheet of Sai_Trust_Data.xlsx
//
//  HOW TO USE
//  1. Power BI Desktop > Home > Transform data > Get Data > Blank Query
//  2. Create ONE query named  pFilePath  (type Text) with the full path of the
//     Excel file, e.g.  "C:\Data\Sai_Trust_Data.xlsx"   (or use a Parameter).
//  3. Create a query named  fnSheet  and paste Block A.
//  4. For each block B1..B21 below: New Query > Blank Query > Advanced Editor,
//     paste the block, rename the query to the name in the block header.
//  5. Disable load for  pFilePath  and  fnSheet  (right-click > uncheck Enable load).
//  6. Close & Apply.
// =====================================================================


// ---------------------------------------------------------------------
// BLOCK A   –   query name:  fnSheet
//  Reads one worksheet, promotes headers, drops blank/unnamed columns
//  (the workbook has stray empty columns), drops fully-empty rows and
//  trims all text.
// ---------------------------------------------------------------------
(SheetName as text) as table =>
let
    Source   = Excel.Workbook(File.Contents(pFilePath), null, true),
    Sheet    = Source{[Item = SheetName, Kind = "Sheet"]}[Data],
    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars = true]),
    // drop columns whose header was empty ("Column12") or that hold no data at all
    NamedOnly = Table.SelectColumns(Promoted,
                   List.Select(Table.ColumnNames(Promoted), each not Text.StartsWith(_, "Column"))),
    NonBlank  = Table.SelectColumns(NamedOnly,
                   List.Select(Table.ColumnNames(NamedOnly),
                       each List.NonNullCount(Table.Column(NamedOnly, _)) > 0)),
    NoEmptyRows = Table.SelectRows(NonBlank, each not List.IsEmpty(List.RemoveMatchingItems(Record.FieldValues(_), {"", null}))),
    Trimmed   = Table.TransformColumns(NoEmptyRows, List.Transform(Table.ColumnNames(NoEmptyRows), (c) => {c, each if _ is text then Text.Trim(_) else _}))
in
    Trimmed


// =====================================================================
//  DIMENSIONS
// =====================================================================

// ---------------------------------------------------------------------
// B1  –  query name:  Dim_Project
// ---------------------------------------------------------------------
let
    Src   = fnSheet("Projects"),
    Typed = Table.TransformColumnTypes(Src, {
              {"Project_ID", type text}, {"Project_Name", type text}, {"Project_Code", type text},
              {"Start_Date", type date}, {"End_Date", type date}, {"Funding_Agency", type text}, {"Active", type logical}}),
    Out   = Table.RemoveColumns(Typed, List.Intersect({{"Logo"}, Table.ColumnNames(Typed)}))
in
    Out

// ---------------------------------------------------------------------
// B2  –  query name:  Dim_SHG
//  One row per SHG with the full location hierarchy flattened in
//  (State > District > Block > Village) and the Project name.
// ---------------------------------------------------------------------
let
    SHG   = fnSheet("SHGs"),
    Keep  = Table.SelectColumns(SHG, {"SHG_ID","SHG_Name","SHG_Code","Location_ID","State_ID","District_ID","Block_ID","Project_ID",
                                      "Assigned_User_ID","Village_Name","Formation_Date","Bank_Name","IFSC","President_ID","Secretary_ID","Treasurer_ID","Status"}),
    St    = Table.NestedJoin(Keep, {"State_ID"},    fnSheet("States"),    {"State_ID"},    "S", JoinKind.LeftOuter),
    St2   = Table.ExpandTableColumn(St, "S", {"State_Name"}),
    Di    = Table.NestedJoin(St2, {"District_ID"},  fnSheet("Districts"), {"District_ID"}, "D", JoinKind.LeftOuter),
    Di2   = Table.ExpandTableColumn(Di, "D", {"District_Name"}),
    Bl    = Table.NestedJoin(Di2, {"Block_ID"},     fnSheet("Blocks"),    {"Block_ID"},    "B", JoinKind.LeftOuter),
    Bl2   = Table.ExpandTableColumn(Bl, "B", {"Block_Name"}),
    Us    = Table.NestedJoin(Bl2, {"Assigned_User_ID"}, fnSheet("Users"), {"User_ID"},    "U", JoinKind.LeftOuter),
    Us2   = Table.ExpandTableColumn(Us, "U", {"User_Name"}, {"Field_Officer"}),
    Typed = Table.TransformColumnTypes(Us2, {{"Formation_Date", type date}}),
    Ren   = Table.RenameColumns(Typed, {{"State_Name","State"},{"District_Name","District"},{"Block_Name","Block"},{"Village_Name","Village"}}),
    // SHG_Name is not unique in the source (29 unique of 30) -> label that is always unique
    Label = Table.AddColumn(Ren, "SHG_Label", each [SHG_Name] & " (" & [SHG_ID] & ")", type text)
in
    Label

// ---------------------------------------------------------------------
// B3  –  query name:  Dim_Member
//  The sheet repeats the whole location block and has TWO "SHG_ID" columns
//  (the 2nd is renamed SHG_ID.1 by Power Query). Keep only member columns.
// ---------------------------------------------------------------------
let
    Src   = fnSheet("SHG_Members"),
    Keep  = Table.SelectColumns(Src, {"Member_ID","SHG_ID","Member_Name","Gender","DOB","Mobile","Joining_Date","Exit_Date","Status"}, MissingField.UseNull),
    Typed = Table.TransformColumnTypes(Keep, {{"DOB", type date},{"Joining_Date", type date},{"Exit_Date", type date}}),
    Age   = Table.AddColumn(Typed, "Age", each if [DOB] = null then null else Number.RoundDown(Duration.Days(Date.From(DateTime.LocalNow()) - [DOB]) / 365.25, 0), Int64.Type),
    AgeGrp= Table.AddColumn(Age, "Age_Group", each if [Age] = null then "Unknown" else if [Age] < 25 then "18-24" else if [Age] < 35 then "25-34" else if [Age] < 45 then "35-44" else if [Age] < 60 then "45-59" else "60+", type text),
    Label = Table.AddColumn(AgeGrp, "Member_Label", each [Member_Name] & " (" & [Member_ID] & ")", type text)
in
    Label

// ---------------------------------------------------------------------
// B4  –  query name:  Dim_FundSource
// ---------------------------------------------------------------------
let
    Src = fnSheet("Fund_Sources"),
    Out = Table.SelectColumns(Src, {"Fund_Source_ID","Source_Type","Source_Name","Organisation_Type","Active"})
in
    Out

// ---------------------------------------------------------------------
// B5  –  query name:  Dim_LoanPurpose
// ---------------------------------------------------------------------
let
    Src = fnSheet("Loan_Purposes")
in
    Src

// ---------------------------------------------------------------------
// B6  –  query name:  Dim_ExpenseCategory
// ---------------------------------------------------------------------
let
    Src = fnSheet("Expense_Categories")
in
    Src


// =====================================================================
//  FACTS   (keys kept: Member_ID for member-level facts, SHG_ID for
//  SHG-level facts, Loan_ID for loan children – this avoids ambiguous
//  filter paths in the model)
// =====================================================================

// ---------------------------------------------------------------------
// B7  –  query name:  Fact_Savings
// ---------------------------------------------------------------------
let
    Src   = fnSheet("Member_Savings"),
    Keep  = Table.SelectColumns(Src, {"Savings_ID","Date","Member_ID","Savings_Type","Amount","Payment_Mode","Financial_Year","Meeting_No","Entered_By"}),
    Typed = Table.TransformColumnTypes(Keep, {{"Date", type date},{"Amount", Currency.Type},{"Meeting_No", Int64.Type}})
in
    Typed

// ---------------------------------------------------------------------
// B8  –  query name:  Fact_Withdrawals
// ---------------------------------------------------------------------
let
    Src   = fnSheet("Savings_Withdrawals"),
    Keep  = Table.SelectColumns(Src, {"Withdrawal_ID","Date","Member_ID","Amount","Reason","Payment_Mode","Approved_By"}),
    Typed = Table.TransformColumnTypes(Keep, {{"Date", type date},{"Amount", Currency.Type}})
in
    Typed

// ---------------------------------------------------------------------
// B9  –  query name:  Fact_FundReceipts
// ---------------------------------------------------------------------
let
    Src   = fnSheet("Fund_Receipts"),
    Keep  = Table.SelectColumns(Src, {"Receipt_ID","Receipt_Date","SHG_ID","Fund_Source_ID","Fund_Type","Amount","Payment_Mode","Purpose","Entered_By"}),
    Typed = Table.TransformColumnTypes(Keep, {{"Receipt_Date", type date},{"Amount", Currency.Type}})
in
    Typed

// ---------------------------------------------------------------------
// B10 –  query name:  Fact_Loans
// ---------------------------------------------------------------------
let
    Src   = fnSheet("Loans"),
    Keep  = Table.SelectColumns(Src, {"Loan_ID","Loan_Number","Member_ID","Loan_Date","Purpose_ID","Principal_Amount","Interest_Rate","Interest_Type",
                                      "Tenure","Installment_Amount","Installment_Frequency","First_Due_Date","Loan_Status","Approved_By"}),
    Typed = Table.TransformColumnTypes(Keep, {{"Loan_Date", type date},{"First_Due_Date", type date},{"Principal_Amount", Currency.Type},
                                               {"Installment_Amount", Currency.Type},{"Interest_Rate", type number},{"Tenure", Int64.Type}})
in
    Typed

// ---------------------------------------------------------------------
// B11 –  query name:  Fact_LoanSchedule
// ---------------------------------------------------------------------
let
    Src   = fnSheet("Loan_Schedule"),
    Keep  = Table.SelectColumns(Src, {"Schedule_ID","Loan_ID","Installment_No","Due_Date","Principal_Due","Interest_Due","Status"}),
    Typed = Table.TransformColumnTypes(Keep, {{"Installment_No", Int64.Type},{"Due_Date", type date},{"Principal_Due", Currency.Type},{"Interest_Due", Currency.Type}}),
    Total = Table.AddColumn(Typed, "Installment_Due", each [Principal_Due] + [Interest_Due], Currency.Type)
in
    Total

// ---------------------------------------------------------------------
// B12 –  query name:  Fact_Repayments
// ---------------------------------------------------------------------
let
    Src   = fnSheet("Loan_Repayments"),
    Keep  = Table.SelectColumns(Src, {"Repayment_ID","Loan_ID","Payment_Date","Principal_Paid","Interest_Paid","Penalty","Total_Paid","Payment_Mode","Receipt_No","Entered_By"}),
    Typed = Table.TransformColumnTypes(Keep, {{"Payment_Date", type date},{"Principal_Paid", Currency.Type},{"Interest_Paid", Currency.Type},
                                               {"Penalty", Currency.Type},{"Total_Paid", Currency.Type}})
in
    Typed

// ---------------------------------------------------------------------
// B13 –  query name:  Fact_LoanApplications
// ---------------------------------------------------------------------
let
    Src   = fnSheet("Loan_Applications"),
    Keep  = Table.SelectColumns(Src, {"Application_ID","Member_ID","Application_Date","Requested_Amount","Purpose","Tenure","Status","Approved_Amount","Approval_Date"}),
    Typed = Table.TransformColumnTypes(Keep, {{"Application_Date", type date},{"Approval_Date", type date},{"Requested_Amount", Currency.Type},
                                               {"Approved_Amount", Currency.Type},{"Tenure", Int64.Type}})
in
    Typed

// ---------------------------------------------------------------------
// B14 –  query name:  Fact_Expenses
// ---------------------------------------------------------------------
let
    Src   = fnSheet("SHG_Expenses"),
    Keep  = Table.SelectColumns(Src, {"Expense_ID","SHG_ID","Expense_Date","Expense_Category_ID","Amount","Payment_Mode","Purpose","Voucher_No"}),
    Typed = Table.TransformColumnTypes(Keep, {{"Expense_Date", type date},{"Amount", Currency.Type}})
in
    Typed

// ---------------------------------------------------------------------
// B15 –  query name:  Fact_Meetings
// ---------------------------------------------------------------------
let
    Src   = fnSheet("SHG_Meetings"),
    Keep  = Table.SelectColumns(Src, {"Meeting_ID","SHG_ID","Meeting_Date","Meeting_No","Facilitator","Total_Members","Members_Present","Agenda"}),
    Typed = Table.TransformColumnTypes(Keep, {{"Meeting_Date", type date},{"Meeting_No", Int64.Type},{"Total_Members", Int64.Type},{"Members_Present", Int64.Type}})
in
    Typed

// ---------------------------------------------------------------------
// B16 –  query name:  Fact_Agriculture
//  The sheet has 57 columns incl. the repeated location block and two
//  "SHG_ID" columns. We keep member-level survey columns only and give
//  every column a clean, DAX-friendly name. One row = one survey record.
// ---------------------------------------------------------------------
let
    Src  = fnSheet("Agriculture"),
    Keep = Table.SelectColumns(Src, {
        "Member_ID","Do you have agricultural land?","Land Unit","Own Land","Agriable land In Ha","Irrigated Land IN Ha","Leased Land","Total Land",
        "Farm Equipment","Did you cultivate crops this year?","Crop Name","Season","Crop Sowning Date","Crop Sown Area","Seeds Quantity In KG",
        "Data Validation","Seed Type","Seed Source","Fertilizer Use","Insect Control","Weed Managment","Irrigation Source","Irrigation Method",
        "Practices Adopted","Critical Input Support","Critical Input Support Type","Demo Plot","Training Status","Training Types","Exposure Status",
        "Exposure Types","Production in quintal","Total Income From Production","Cultivation Cost","Net Profit","Major Crops Grown In Last Year",
        "Last Year Area in Ha","Last Year Production","Last Year Total Income From Production","Last Year Total cultivation Cost","Last Year Profit","Data Submit Date"},
        MissingField.UseNull),
    Ren = Table.RenameColumns(Keep, {
        {"Do you have agricultural land?","Has_Land"},{"Land Unit","Land_Unit"},{"Own Land","Own_Land_Ha"},{"Agriable land In Ha","Agri_Land_Ha"},
        {"Irrigated Land IN Ha","Irrigated_Land_Ha"},{"Leased Land","Leased_Land_Ha"},{"Total Land","Total_Land_Ha"},{"Farm Equipment","Farm_Equipment"},
        {"Did you cultivate crops this year?","Cultivated"},{"Crop Name","Crop"},{"Crop Sowning Date","Sowing_Date"},{"Crop Sown Area","Sown_Area_Ha"},
        {"Seeds Quantity In KG","Seed_Qty_Kg"},{"Data Validation","Validation_Status"},{"Seed Type","Seed_Type"},{"Seed Source","Seed_Source"},
        {"Fertilizer Use","Fertilizer"},{"Insect Control","Insect_Control"},{"Weed Managment","Weed_Management"},{"Irrigation Source","Irrigation_Source"},
        {"Irrigation Method","Irrigation_Method"},{"Practices Adopted","Practice_Adopted"},{"Critical Input Support","Input_Support"},
        {"Critical Input Support Type","Input_Support_Type"},{"Demo Plot","Demo_Plot"},{"Training Status","Training"},{"Training Types","Training_Type"},
        {"Exposure Status","Exposure"},{"Exposure Types","Exposure_Type"},{"Production in quintal","Production_Qtl"},
        {"Total Income From Production","Income"},{"Cultivation Cost","Cultivation_Cost"},{"Net Profit","Net_Profit"},
        {"Major Crops Grown In Last Year","LY_Crop"},{"Last Year Area in Ha","LY_Area_Ha"},{"Last Year Production","LY_Production_Qtl"},
        {"Last Year Total Income From Production","LY_Income"},{"Last Year Total cultivation Cost","LY_Cost"},{"Last Year Profit","LY_Profit"},
        {"Data Submit Date","Submit_Date"}}),
    Typed = Table.TransformColumnTypes(Ren, {{"Sowing_Date", type date},{"Submit_Date", type date},
        {"Own_Land_Ha", type number},{"Agri_Land_Ha", type number},{"Irrigated_Land_Ha", type number},{"Leased_Land_Ha", type number},{"Total_Land_Ha", type number},
        {"Sown_Area_Ha", type number},{"Seed_Qty_Kg", type number},{"Production_Qtl", type number},{"Income", Currency.Type},{"Cultivation_Cost", Currency.Type},
        {"Net_Profit", Currency.Type},{"LY_Area_Ha", type number},{"LY_Production_Qtl", type number},{"LY_Income", Currency.Type},{"LY_Cost", Currency.Type},{"LY_Profit", Currency.Type}}),
    // fill "no crop" rows so slicers show a label instead of (Blank)
    Fill  = Table.ReplaceValue(Typed, null, "No crop this year", Replacer.ReplaceValue, {"Crop","Season"}),
    Idx   = Table.AddIndexColumn(Fill, "Record_ID", 1, 1, Int64.Type)
in
    Idx
