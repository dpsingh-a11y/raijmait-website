"""Reads Sai_Trust_Data.xlsx, runs data-quality checks and exports dashboard_data.json."""
import sys, json, pandas as pd
src = sys.argv[1]; out = sys.argv[2]
x = {k: d.dropna(axis=1, how='all') for k, d in pd.read_excel(src, sheet_name=None).items()}
d = lambda s: s.dt.strftime('%Y-%m-%d').where(s.notna(), None)
def rec(df): return json.loads(df.astype(object).where(df.notna(), None).to_json(orient='records'))

st = x['States'].set_index('State_ID').State_Name; di = x['Districts'].set_index('District_ID').District_Name
bl = x['Blocks'].set_index('Block_ID').Block_Name; pr = x['Projects'].set_index('Project_ID').Project_Name
us = x['Users'].set_index('User_ID').User_Name
S = x['SHGs'][['SHG_ID','SHG_Name','Location_ID','State_ID','District_ID','Block_ID','Project_ID','Village_Name','Formation_Date','Bank_Name','Status']].copy()
S['Formation_Date'] = d(S.Formation_Date)
S['State']=S.State_ID.map(st); S['District']=S.District_ID.map(di); S['Block']=S.Block_ID.map(bl); S['Project']=S.Project_ID.map(pr)
M = x['SHG_Members'][['Member_ID','SHG_ID','Member_Name','Gender','DOB','Joining_Date','Status']].copy()
M['DOB']=d(M.DOB); M['Joining_Date']=d(M.Joining_Date)
sv = x['Member_Savings'][['Savings_ID','Date','SHG_ID','Member_ID','Amount','Payment_Mode','Financial_Year']].copy(); sv['Date']=d(sv.Date)
wd = x['Savings_Withdrawals'][['Withdrawal_ID','Date','SHG_ID','Member_ID','Amount','Reason']].copy(); wd['Date']=d(wd.Date)
fr = x['Fund_Receipts'][['Receipt_ID','Receipt_Date','SHG_ID','Fund_Source_ID','Fund_Type','Amount','Payment_Mode','Project_ID']].copy(); fr['Receipt_Date']=d(fr.Receipt_Date)
fr['Source']=fr.Fund_Source_ID.map(x['Fund_Sources'].set_index('Fund_Source_ID').Source_Name)
fr['Source_Type']=fr.Fund_Source_ID.map(x['Fund_Sources'].set_index('Fund_Source_ID').Source_Type)
lp = x['Loan_Purposes'].set_index('Purpose_ID').Purpose
ln = x['Loans'][['Loan_ID','SHG_ID','Member_ID','Loan_Date','Purpose_ID','Principal_Amount','Interest_Rate','Interest_Type','Tenure','Installment_Amount','Loan_Status']].copy()
ln['Loan_Date']=d(ln.Loan_Date); ln['Purpose']=ln.Purpose_ID.map(lp)
ls = x['Loan_Schedule'][['Schedule_ID','Loan_ID','Installment_No','Due_Date','Principal_Due','Interest_Due','Status']].copy(); ls['Due_Date']=d(ls.Due_Date)
ls['SHG_ID']=ls.Loan_ID.map(ln.set_index('Loan_ID').SHG_ID)
rp = x['Loan_Repayments'][['Repayment_ID','Loan_ID','Member_ID','SHG_ID','Payment_Date','Principal_Paid','Interest_Paid','Penalty','Total_Paid','Payment_Mode']].copy(); rp['Payment_Date']=d(rp.Payment_Date)
la = x['Loan_Applications'][['Application_ID','SHG_ID','Member_ID','Application_Date','Requested_Amount','Purpose','Status','Approved_Amount']].copy(); la['Application_Date']=d(la.Application_Date)
ex = x['SHG_Expenses'][['Expense_ID','SHG_ID','Expense_Date','Expense_Category_ID','Amount','Payment_Mode']].copy(); ex['Expense_Date']=d(ex.Expense_Date)
ex['Category']=ex.Expense_Category_ID.map(x['Expense_Categories'].set_index('Expense_Category_ID').Expense_Category)
mt = x['SHG_Meetings'][['Meeting_ID','SHG_ID','Meeting_Date','Meeting_No','Total_Members','Members_Present']].copy(); mt['Meeting_Date']=d(mt.Meeting_Date)
A = x['Agriculture'].copy()
ren = {'Do you have agricultural land?':'Has_Land','Own Land':'Own','Agriable land In Ha':'Agri','Irrigated Land IN Ha':'Irrigated','Leased Land':'Leased','Total Land':'Total_Land',
 'Farm Equipment':'Equipment','Did you cultivate crops this year?':'Cultivated','Crop Name':'Crop','Crop Sown Area':'Area','Seed Type':'Seed_Type','Seed Source':'Seed_Source',
 'Fertilizer Use':'Fertilizer','Insect Control':'Insect','Weed Managment':'Weed','Irrigation Source':'Irr_Source','Irrigation Method':'Irr_Method','Practices Adopted':'Practice',
 'Critical Input Support':'Input_Support','Critical Input Support Type':'Input_Type','Demo Plot':'Demo','Training Status':'Training','Training Types':'Training_Type','Exposure Status':'Exposure',
 'Production in quintal':'Production','Total Income From Production':'Income','Cultivation Cost':'Cost','Net Profit':'Profit','Major Crops Grown In Last Year':'LY_Crop','Last Year Area in Ha':'LY_Area',
 'Last Year Production':'LY_Prod','Last Year Total Income From Production':'LY_Income','Last Year Total cultivation Cost':'LY_Cost','Last Year Profit':'LY_Profit','Data Submit Date':'Submit_Date','Crop Sowning Date':'Sowing_Date'}
A = A.rename(columns=ren)
A['Submit_Date']=d(A.Submit_Date); A['Sowing_Date']=d(A.Sowing_Date)
A = A.loc[:, ~A.columns.duplicated()]
keep = ['Member_ID','SHG_ID','Season']+[c for c in ren.values() if c in A.columns and c not in ('Seeds Quantity In KG',)]
A = A[[c for c in dict.fromkeys(keep)]]
A['SHG_ID'] = A.Member_ID.map(M.set_index('Member_ID').SHG_ID)  # SHG_ID via member
A['Row_ID'] = range(1, len(A)+1)

data = dict(shgs=rec(S), members=rec(M), savings=rec(sv), withdrawals=rec(wd), funds=rec(fr), loans=rec(ln), schedule=rec(ls),
            repayments=rec(rp), applications=rec(la), expenses=rec(ex), meetings=rec(mt), agri=rec(A), users=rec(x['Users'][['User_ID','User_Name']]))
json.dump(data, open(out,'w'), separators=(',',':'))

# ---- data-quality report ----
print('rows:', {k:len(v) for k,v in data.items()})
fy = x['SHGs'].set_index('SHG_ID').Formation_Date
b = (pd.to_datetime(sv.Date) < sv.SHG_ID.map(fy)).sum(); print('savings dated before SHG formation:', b)
print('loans before SHG formation:', (pd.to_datetime(ln.Loan_Date) < ln.SHG_ID.map(fy)).sum())
mc = M.SHG_ID.value_counts(); print('meetings Total_Members vs actual members mismatch:', (mt.Total_Members != mt.SHG_ID.map(mc)).sum(), 'of', len(mt))
print('SHG blank cols:', [c for c in x['SHGs'].columns if x['SHGs'][c].isna().all()], 'Current_balance non-null:', x['SHGs'].Current_balance.notna().sum())
print('principal paid > principal:', (rp.groupby('Loan_ID').Principal_Paid.sum() > ln.set_index('Loan_ID').Principal_Amount).sum())
print('loan total_paid mismatch:', (rp.Principal_Paid+rp.Interest_Paid+rp.Penalty != rp.Total_Paid).sum())
print('withdrawal rest mismatch:', (x['Savings_Withdrawals']['Available Balance']-x['Savings_Withdrawals'].Amount != x['Savings_Withdrawals'].Rest_balance).sum())
print('withdrawal > member savings:', sum(w.Amount > sv[sv.Member_ID==w.Member_ID].Amount.sum() for w in wd.itertuples()))
print('SHG ids with no members:', (~S.SHG_ID.isin(M.SHG_ID)).sum(), '| members without loan data:', M.Member_ID.isin(ln.Member_ID).sum())
print('Loan schedule paid vs repayments:', (ls.Status=='Paid').sum(), len(rp))
print('overdue pending rows (due<2026-10-01):', ((ls.Status=='Pending') & (pd.to_datetime(ls.Due_Date) < '2026-10-01')).sum())
print('agri rows no crop:', A.Crop.isna().sum(), '| profit != income-cost:', ((A.Income-A.Cost-A.Profit).abs()>1).sum())
print('Total_Land != own+leased:', ((A.Total_Land-(A.Own+A.Leased)).abs()>0.011).sum())
print('Fund receipts total', fr.Amount.sum(), 'savings', sv.Amount.sum(), 'loans', ln.Principal_Amount.sum())
