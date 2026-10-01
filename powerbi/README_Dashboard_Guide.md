# Sai Trust SHG Dashboard: Power BI build guide

Source workbook: `Sai_Trust_Data.xlsx` (22 sheets, fictional test data).
A working preview of the finished dashboard, built from the same data and the same measure logic, is in `dashboard.html` (open it in a browser).

| File | What it is |
|---|---|
| `SaiTrust/` (and `SaiTrust_PBIP.zip`) | **Ready-to-open Power BI Project**: `SaiTrust.pbip` with the full model (18 tables, 25 relationships, 94 measures) and a 6-page report with 105 visuals (including slicers and navigation). See section 0 |
| `make_pbip.py` | Regenerates the `SaiTrust/` project from the two files below |
| `01_PowerQuery_Import.m` | Power Query for every sheet: one helper function plus 6 dimension and 10 fact queries |
| `02_DAX_Measures.dax` | Date table, measure table and 94 measures in six folders |
| `03_Sai_Trust_Theme.json` | Power BI theme (View > Themes > Browse for themes) |
| `dashboard.html` | Interactive preview of all six pages |
| `build_data.py`, `dashboard_template.html` | Regenerate the preview from a new copy of the workbook: `python3 build_data.py <xlsx> data.json`, then paste the JSON into the template at `/*DATA*/` |

## 0. Open the Power BI Project (fastest route)

A `.pbix` file is a compressed binary that only Power BI Desktop can write, so this repo ships the same thing as a **Power BI Project** (`SaiTrust/SaiTrust.pbip`), the text-based format Desktop opens directly.

1. Install the latest Power BI Desktop (Windows). Unzip `SaiTrust_PBIP.zip` and put `Sai_Trust_Data.xlsx` somewhere stable.
2. File > Options and settings > Options > Preview features: turn on **Power BI Project (.pbip) save option**, **Store semantic model in TMDL format** and **Store reports using enhanced metadata format (PBIR)** (newer versions have these on by default). Restart Desktop.
3. File > Open report > Browse this device > pick `SaiTrust.pbip`.
4. Home > Transform data > Edit parameters > set **pFilePath** to the full path of your workbook (default is `C:\SaiTrust\Sai_Trust_Data.xlsx`). Close & Apply to load the data.
5. **File > Save as** and choose a `.pbix` file. That is your `.pbix`.

The report files were checked against Microsoft's published PBIR schemas (114 files, no errors), and every column and measure the visuals use was cross-checked against the model. The project has **not been opened in Power BI Desktop yet**, because Desktop is not available where it was generated. If Desktop reports an error on opening or refresh, send me the message and I will fix it.

## 1. Sheets and what each one is

| Sheet | Rows | Grain / purpose | Power BI table |
|---|---|---|---|
| README | – | Notes only | not loaded |
| Users | 25 | Field staff. Email and role sit under blank headers | used only to name the field officer |
| Projects | 15 | Project, dates, funding agency | `Dim_Project` |
| States, Districts, Blocks, Locations | 15 / 23 / 30 / 30 | Location hierarchy | flattened into `Dim_SHG` |
| SHGs | 30 | One row per group, with the location block repeated | `Dim_SHG` |
| SHG_Members | 105 | One row per member, location block repeated | `Dim_Member` |
| Loan_Purposes | 45 | Lookup | `Dim_LoanPurpose` |
| Fund_Sources | 26 | Lookup | `Dim_FundSource` |
| Expense_Categories | 40 | Lookup | `Dim_ExpenseCategory` |
| Fund_Receipts | 20 | Money received by an SHG | `Fact_FundReceipts` |
| Member_Savings | 125 | Monthly saving by member | `Fact_Savings` |
| Savings_Withdrawals | 30 | Savings taken out | `Fact_Withdrawals` |
| Loan_Applications | 20 | Request and approval | `Fact_LoanApplications` |
| Loans | 19 | Loan issued | `Fact_Loans` |
| Loan_Schedule | 57 | Instalment due dates | `Fact_LoanSchedule` |
| Loan_Repayments | 19 | Payments received | `Fact_Repayments` |
| SHG_Expenses | 20 | Group spending | `Fact_Expenses` |
| SHG_Meetings | 20 | Meetings and attendance | `Fact_Meetings` |
| Agriculture | 100 | Farm survey records (57 columns) | `Fact_Agriculture` |

Business flow from the README: Project > Location > SHG > Member; Fund Source > Fund Receipt > SHG; Member > Savings / Withdrawals; Member > Loan > Schedule / Repayment; SHG > Expenses.

## 2. Import steps

1. In Power BI Desktop, open Transform data and follow the header of `01_PowerQuery_Import.m`: create `pFilePath` (the path to the workbook), then `fnSheet`, then one blank query per block B1 to B16. (The Project in section 0 already contains all of this.)
2. Close & Apply, then run the DAX from `02_DAX_Measures.dax`: `Dim_Date`, `_Measures`, then the measures.

`fnSheet` handles the messy parts of the workbook: unnamed columns, fully empty columns (several sheets have 10 to 20 stray blank columns), empty rows and padded text.

## 3. Model (star schema)

Each fact table has exactly one filter path to `Dim_SHG`, so there are no ambiguous relationships. All relationships are many-to-one, single direction, from the dimension to the fact.

```
Dim_Project --< Dim_SHG --< Dim_Member --< Fact_Savings
                    |            |--------< Fact_Withdrawals
                    |            |--------< Fact_Loans
                    |            |--------< Fact_LoanSchedule
                    |            |--------< Fact_Repayments
                    |            |--------< Fact_LoanApplications
                    |            '--------< Fact_Agriculture
                    |--------------------< Fact_FundReceipts
                    |--------------------< Fact_Expenses
                    '--------------------< Fact_Meetings
Dim_FundSource   --< Fact_FundReceipts[Fund_Source_ID]
Dim_LoanPurpose  --< Fact_Loans[Purpose_ID]
Dim_ExpenseCategory --< Fact_Expenses[Expense_Category_ID]
Dim_Date[Date]   --< Savings[Date], Withdrawals[Date], FundReceipts[Receipt_Date], Loans[Loan_Date],
                     Repayments[Payment_Date], Expenses[Expense_Date], Meetings[Meeting_Date],
                     LoanSchedule[Due_Date], LoanApplications[Application_Date], Agriculture[Submit_Date]
```

Loan_Schedule and Loan_Repayments link through the member (not through Loans) so that no table has two filter paths from `Dim_Date`. The loan register therefore uses the per-loan measures `Loan Repaid`, `Loan Outstanding` and `Loan Overdue Instalments`, which match on Loan_ID with TREATAS. A purpose slicer filters Loans but not Repayments.

Keep only one active relationship from each fact to `Dim_Date`. Mark `Dim_Date` as the date table.

## 4. Pages

Apply `03_Sai_Trust_Theme.json`. Put these slicers in a top bar on every page (Sync slicers across pages): **Project**, **State**, **District**, **SHG_Label**, and **Financial Year** from `Dim_Date`.

### Page 1: Overview
- Alert text box bound to a measure: *"20 instalments worth ₹34,367 are overdue"* (use `Overdue Installments #` and `Overdue Principal`).
- 8 cards: `SHG Count`, `Net Savings`, `Fund Received`, `Loans Disbursed`, `Outstanding Principal`, `Repayment Rate %`, `PAR %`, `Estimated Cash Balance`.
- Line chart: `Dim_Date[Month Year]` against `Total Savings`, `Loans Disbursed`, `Total Collected`.
- Bar charts: `Fund Received` by `Fund_Type`; `Loans Disbursed` by `Dim_LoanPurpose[Purpose]`; `SHG Count` by `District`; `Fund Received` by `Project_Name`.

### Page 2: Savings & Funds
- Cards: `Total Savings`, `Total Withdrawals`, `Net Savings`, `Savings per Member`, `Fund Received`, `Total Expenses`, `Expense % of Funds`.
- Clustered column: `Total Savings` and `Total Withdrawals` by month.
- Bars: `Net Savings` by `SHG_Label` (Top N = 10); `Total Withdrawals` by `Reason`; `Fund Received` by `Source_Name`; `Total Expenses` by `Expense_Category`.
- Table: fund receipts (date, SHG, source, type, mode, amount).

### Page 3: Loans
- Cards: `Loans Disbursed`, `Outstanding Principal`, `Total Collected`, `Repayment Rate %`, `PAR %` (conditional colour from `PAR Colour`), `Avg Loan Size`, `Upcoming Due (30 days)`, `Approval Rate %`.
- Stacked column: instalments by `Due_Date` month, legend = `Fact_LoanSchedule[Status]`. For an Overdue legend, add a calculated column `Schedule Bucket = IF([Status]="Paid","Paid",IF([Due_Date]<TODAY(),"Overdue","Due later"))`.
- Bars: `Outstanding Principal` by SHG; `Loans Disbursed` by purpose; applications `Applied Amount` vs `Approved Amount` by status.
- Table (loan register): Loan_ID, member, SHG, purpose, principal, `Principal Collected`, `Outstanding Principal`, `Overdue Installments #` with a red icon rule when above 0.

### Page 4: SHGs & Members
- Cards: `SHG Count`, `Members`, `Female %`, `Avg Members per SHG`, `Meetings Held`, `Attendance %`.
- Bars: `Members` by SHG; `Members` by `Age_Group`; `Attendance %` by SHG (sort ascending).
- Line: running count of SHGs by `Formation_Date` month.
- Matrix scorecard: SHG rows with `Members`, `Net Savings`, `Outstanding Principal`, `Overdue Principal`, `Attendance %`.
- Optional: a map visual on `Dim_SHG[District]` (Bing maps needs the State as a location hint).

### Page 5: Agriculture
- Cards: `Farmers Surveyed`, `Area Sown (ha)`, `Crop Income`, `Net Profit`, `Benefit Cost Ratio`, `Yield (qtl/ha)`, `Training Coverage %`, `Irrigated % of Agri Land`.
- Bars: `Net Profit` by `Crop` (Top N = 12); `Area Sown (ha)` by crop; `Net Profit` by `Season`.
- "Programme reach" bar: `Training Coverage %`, `Input Support %`, `Exposure Visit %`, `Demo Plot %`, `Improved Practice %` (use a small disconnected table or the multi-row card).
- Columns: `Profit per Record (Trained)` vs `Profit per Record (Not trained)`; `Net Profit` vs `Last Year Profit`.
- Bars by record count: `Irrigation_Source`, `Irrigation_Method`, `Practice_Adopted`, `Seed_Source`.

### Page 6: Data notes
Text box with the quality notes in section 6 below.

### Interaction settings
- Turn on **Drill-through** from SHG name to a detail page showing that SHG's members, loans and meetings.
- Add bookmarks for the filter panel and a "Reset filters" button.
- Add tooltips pages for SHG (members, savings, loans) if you want hover detail.

## 5. Measure definitions that need agreement

| Measure | Definition used |
|---|---|
| Outstanding Principal | Loans disbursed minus principal repaid |
| Overdue | Pending instalment with a due date before **today** (`TODAY()`). Replace with a fixed date parameter for reporting as of a month end |
| PAR % | Overdue principal divided by outstanding principal. Healthy up to 5%, watch up to 10%, at risk above 10% |
| Repayment Rate % | Principal repaid divided by principal due up to today |
| Estimated Cash Balance | Funds + savings + all repayments − withdrawals − loans given − expenses. It is an estimate because the workbook has no opening balance or bank statement |
| Attendance % | Members present divided by Total_Members recorded on the meeting |
| Agriculture totals | Summed across survey records, because land and last-year figures differ between a member's rows |

## 6. Data quality notes found while reading every sheet

1. The README states all data is fictional, so the figures are for building and testing the dashboard.
2. 46 of 125 savings entries and 7 of 19 loans are dated before their SHG's formation date.
3. 17 of 20 meetings record a Total_Members figure of 16 to 18, but the SHGs have only 3 to 5 registered members, so Attendance % is not reliable.
4. 4 withdrawals are larger than the member's recorded savings.
5. The SHGs sheet has balance columns (`Current_balance`, `Toatal_Balance` [sic], `Distributed_Loan_Balance`, `Total_Recover_balance`, `Total_Interest`). Only `Current_balance` has values, and they do not reconcile with transactions. The dashboard calculates balances from transactions.
6. `SHGs`, `SHG_Members` and `Agriculture` repeat the whole location block, and the last two have two `SHG_ID` columns. The query keeps only the columns each table needs.
7. `Users` has email and role values under blank headers.
8. One SHG name is used twice. Use `SHG_Label` (name plus ID) in visuals.
9. 24 of 30 SHGs are in Rajasthan, 13 in Dholpur.
10. Loan status is "Active" for every loan, and every savings entry is "Monthly Savings", so slicing on those has no effect yet.
11. Agriculture: 100 records for 65 members. 8 records say no cultivation, so crop and season show "No crop this year" in Power BI.

## 7. Suggested next steps
- Replace the sample workbook with the real one. The queries read by column name, so extra rows work without changes.
- Decide how Loan_Schedule status should be updated when a repayment is entered. Today it is a separate manual field.
- Add a collection-efficiency measure by month once real due dates and payments line up.
