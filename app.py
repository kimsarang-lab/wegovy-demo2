from pathlib import Path
import html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='상품 대안 비교 | 시연 2', page_icon='▦', layout='wide')
st.markdown('<style>.block-container{max-width:1500px;padding-top:2rem} h1{letter-spacing:-1px} div[data-testid="stMetric"]{background:#fff;border-radius:12px;padding:16px} .eyebrow{color:#008c82;font-weight:700;letter-spacing:2px}</style>',unsafe_allow_html=True)
st.markdown('<div class="eyebrow">DEMO 02 · PRODUCT EXPLORER</div>',unsafe_allow_html=True)
st.title('위고비 약제비 보험, 보장과 비용 살펴보기')
st.caption('① 고객 입장에서 보장 비교 → ② 선택한 상품을 보험사 입장에서 확인')
path=Path(__file__).parent/'data/results.csv'
upload=st.sidebar.file_uploader('결과 CSV 미리보기',type='csv',help='업로드는 현재 세션에만 적용됩니다. 영구 변경은 data/results.csv를 교체하세요.')
try:
 df=pd.read_csv(upload if upload is not None else path)
 required=['product_id','product_name','benefit_krw','limit_count','waiting_days','scenario','annual_premium_krw','expected_count','expected_benefit_pv_krw','profit_npv_krw','benefit_ae','max_funding_gap_krw','data_status','source_note']
 missing=set(required)-set(df.columns)
 if missing: raise ValueError('필수 열 누락: '+', '.join(sorted(missing)))
 nums=required[2:5]+required[6:12]
 for c in nums: df[c]=pd.to_numeric(df[c],errors='raise')
 if not np.isfinite(df[nums].to_numpy()).all(): raise ValueError('숫자 열에는 빈칸/무한값을 사용할 수 없습니다.')
 if df[required].isna().any().any(): raise ValueError('필수 열에 빈칸이 있습니다.')
 if df.duplicated(['product_id','scenario']).any(): raise ValueError('상품 ID·시나리오 중복입니다.')
 if set(df.scenario)!= {'기준','이용 증가'}: raise ValueError('시나리오는 기준/이용 증가 두 가지여야 합니다.')
 for pid,g in df.groupby('product_id'):
  if len(g)!=2: raise ValueError(f'{pid}: 두 시나리오가 필요합니다.')
  for c in ['product_name','benefit_krw','limit_count','waiting_days','annual_premium_krw']:
   if g[c].nunique()!=1: raise ValueError(f'{pid}: {c}는 시나리오 간 같아야 합니다.')
 if (df[[c for c in nums if c!='profit_npv_krw']]<0).any().any(): raise ValueError('손익 외 숫자는 음수일 수 없습니다.')
 if (df.expected_count>df.limit_count).any(): raise ValueError('기대 지급 횟수가 통산 한도를 초과합니다.')
 if df[df.scenario=='기준'].duplicated(['waiting_days','limit_count','benefit_krw']).any(): raise ValueError('동일 설계 조건이 중복됩니다.')
except Exception as e:
 st.error(f'CSV를 읽을 수 없습니다: {e}');st.stop()
if df.data_status.str.contains('가상').any(): st.warning('화면 검토용 가상 데이터 · 실제 보험료, 수익성 또는 상품 승인 근거가 아닙니다.')
else: st.info('데이터 구분: '+ ' / '.join(df.data_status.unique())+' · 업로드된 값의 타당성은 별도 검토가 필요합니다.')
st.caption('10년 만기 · 10년납 | 28일분 적격 조제당 정액 지급 | 환급금 없음 | 금액: 가입자 1인당 | 연령·성별·산출 기준일: 미설정')
with st.expander('이 시연의 대상과 해석'):
 st.write('연구에서 정한 가입 조건을 충족한 가상 가입자 집단의 결과입니다. 개인별 가입 가능 여부나 개인 맞춤 수령액을 예측하지 않습니다. 정확한 BMI·연령 등의 가입 조건은 연구 최종안에 맞춰 확정해야 합니다.')
 st.write('예상 수령액은 치료하지 않는 가입자도 포함한 집단 평균입니다. 최대 보장액은 모두 받는 금액이 아닙니다. 기존 사망보험금 변화는 이 화면에 합산하지 않습니다.')
if 'stage' not in st.session_state:st.session_state.stage='customer'
def stage(v):st.session_state.stage=v
st.sidebar.header('보장 조건')
wait=st.sidebar.radio('보장이 시작되기까지',sorted(df.waiting_days.unique()),index=len(df.waiting_days.unique())-1,format_func=lambda x:f'가입 후 {x:g}일',help='보험금 지급 대기기간입니다.')
df['monthly']=df.annual_premium_krw/12
df['max_cover']=df.benefit_krw*df.limit_count
base=df[(df.waiting_days==wait)&(df.scenario=='기준')].copy()
ids=base.product_id.tolist()
if not ids:st.info('해당 조건의 상품이 없습니다.');st.stop()
if st.session_state.get('chosen') not in ids:st.session_state.chosen=ids[min(1,len(ids)-1)]
name_map=df.drop_duplicates('product_id').set_index('product_id').product_name.to_dict()
fmt=lambda v:f'{v:,.0f}원'
st.sidebar.caption('1회 지급액과 최대 지급 횟수는 지도 또는 상품 목록에서 선택합니다.')
if st.session_state.stage=='customer':
 st.header('① 내가 내는 보험료와 받을 수 있는 보장')
 st.write('점을 눌러 상품을 비교해 보세요. 오른쪽일수록 최대 보장이 크고, 아래쪽일수록 보험료가 낮습니다.')
 left,right=st.columns([2.3,1])
 with left:
  fig=go.Figure()
  for i,(limit,g) in enumerate(base.groupby('limit_count')):
   fig.add_trace(go.Scatter(x=g.max_cover/10000,y=g.monthly,mode='markers+text',name=f'최대 {limit:g}회 지급',text=g.product_name,textposition='top center',customdata=[[r.product_id,r.benefit_krw/10000,r.limit_count] for _,r in g.iterrows()],marker=dict(size=[27 if p==st.session_state.chosen else 19 for p in g.product_id],symbol=['circle','diamond','square'][i%3],color=['#008C82' if p==st.session_state.chosen else '#C9D5E4' for p in g.product_id],line=dict(color='#29425F',width=2)),hovertemplate='<b>%{text}</b><br>월 기준 보험료 %{y:,.0f}원<br>최대 보장 %{x:g}만 원<br>조제당 %{customdata[1]:g}만 원 · 최대 %{customdata[2]:g}회<extra></extra>'))
  fig.update_layout(height=540,clickmode='event+select',dragmode='pan',plot_bgcolor='#FFFFFF',paper_bgcolor='rgba(0,0,0,0)',legend=dict(orientation='h',y=1.12),margin=dict(l=25,r=20,t=40,b=20),font=dict(color='#20374F'))
  fig.update_xaxes(title='최대로 받을 수 있는 보험금 (만 원)',range=[0,float(df.max_cover.max()/10000)*1.15])
  fig.update_yaxes(title='월 기준 보험료 (원 · 연납액÷12)',range=[0,float(df.monthly.max())*1.2])
  key=f'customer_map_{wait}'
  def select_point():
   pts=st.session_state.get(key,{}).get('selection',{}).get('points',[])
   if pts:
    data=pts[-1].get('customdata',[])
    if data and data[0] in ids:st.session_state.chosen=data[0]
  st.plotly_chart(fig,key=key,on_select=select_point,selection_mode='points',use_container_width=True,config={'displaylogo':False})
  st.caption('청록색은 선택한 상품입니다. 색상은 고객이나 보험사의 이익·손실을 의미하지 않습니다. 겹치는 점은 오른쪽 상품 목록에서 선택하세요.')
 with right:
  pid=st.selectbox('살펴볼 상품',ids,key='chosen',format_func=lambda p:name_map[p])
  r=base[base.product_id==pid].iloc[0]
  st.subheader(r.product_name)
  st.metric('월 기준 보험료',fmt(r.monthly),help='연납 보험료를 12로 나눈 참고값이며 실제 월납 보험료가 아닙니다.')
  st.metric('최대로 받을 수 있는 보험금',fmt(r.max_cover))
  st.write(f'28일분 적격 조제당 **{r.benefit_krw/10000:g}만 원**')
  st.write(f'보험기간 전체에서 **최대 {r.limit_count:g}회** 지급')
  st.write(f'보장 시작 대기기간 **{wait:g}일**')
  st.caption(f'연납 보험료 {fmt(r.annual_premium_krw)} · 10년 보장·10년납')
 st.subheader('내가 내는 돈과 받을 수 있는 돈')
 c=st.columns(3)
 c[0].metric('10년간 예정 납입액',fmt(r.annual_premium_krw*10),help='연납액×10. 10년 동안 전액 납입할 때의 명목 합계이며 해지·사망 등을 반영한 기대 납입액이 아닙니다.')
 c[1].metric('최대 보장액',fmt(r.max_cover),help='지급 조건을 충족하여 한도까지 지급받았을 때의 명목 금액입니다.')
 c[2].metric('연구 가정상 예상 수령액',fmt(r.expected_benefit_pv_krw),help='전체 가입자 1인당 평균 보험금 지급액의 현재가치입니다. 개인이 실제 받는 금액과 다릅니다.')
 st.info('최대 보장액과 예상 수령액은 다릅니다. 예정 납입액은 명목 합계, 예상 수령액은 현재가치이므로 두 숫자를 직접 빼서 고객의 이익이라고 계산하지 않습니다.')
 # A valid net comparison is only available when both expectation/PV fields exist.
 if 'expected_premium_pv_krw' in df and pd.notna(r.get('expected_premium_pv_krw')):
  pp=pd.to_numeric(r.expected_premium_pv_krw,errors='coerce')
  if pd.notna(pp) and np.isfinite(pp) and pp>=0:
   st.metric('평균 예상 수령액 − 평균 예상 납입액 (현재가치)',fmt(r.expected_benefit_pv_krw-pp))
   st.caption('동일 집단·10년·동일 할인 기준이라는 전제의 현금흐름 차이입니다. 개인별 이익이나 보험의 위험보장 가치를 뜻하지 않습니다.')
 st.subheader('상품 두 개 비교하기')
 chosen=st.multiselect('비교할 상품',ids,default=ids[1:2]+ids[3:4] if len(ids)>3 else ids[:2],max_selections=2,key=f'compare_{wait}',format_func=lambda p:name_map[p])
 show=base[base.product_id.isin(chosen)][['product_name','monthly','benefit_krw','limit_count','max_cover']].rename(columns={'product_name':'상품','monthly':'월 기준 보험료(원)','benefit_krw':'조제당 지급액(원)','limit_count':'최대 지급횟수','max_cover':'최대 보장액(원)'})
 st.dataframe(show.set_index('상품').T,use_container_width=True)
 st.divider()
 st.subheader('그렇다면, 이 보장을 제공하는 보험사는 어떨까요?')
 st.button('선택한 상품을 보험사 입장에서 보기 →',type='primary',on_click=stage,args=('insurer',))
else:
 st.button('← 고객 입장에서 다시 비교하기',on_click=stage,args=('customer',))
 st.header('② 선택한 상품을 보험사 입장에서 살펴보기')
 pid=st.selectbox('분석할 상품',ids,key='chosen',format_func=lambda p:name_map[p])
 r=base[base.product_id==pid].iloc[0]
 st.caption(f'{r.product_name} · 조제당 {r.benefit_krw/10000:g}만 원 · 최대 {r.limit_count:g}회 · 대기기간 {wait:g}일')
 scenario=st.radio('치료 이용 상황',['기준','이용 증가'],format_func=lambda x:'예상대로 이용' if x=='기준' else '예상보다 많이 이용',horizontal=True)
 pair=df[df.product_id==pid].set_index('scenario')
 cur=pair.loc[scenario]
 st.info('현재 화면의 수입·지출·손익은 모두 가입자 1인당, 10년 분석기간, 현재가치 기준입니다. 시나리오를 바꿔도 보험료는 유지됩니다.')
 # Optional results support real data without inventing an insurer decomposition.
 income=pd.to_numeric(cur.get('premium_income_pv_krw',float('nan')),errors='coerce')
 expense=pd.to_numeric(cur.get('expense_pv_krw',float('nan')),errors='coerce')
 mock=str(cur.data_status)=='가상 예시값'
 if mock and (pd.isna(income) or pd.isna(expense)):
  income=cur.annual_premium_krw*8.5;expense=income*.2+20000
  st.caption('가상값 구성: 보험료 수입 PV=연납액×8.5, 사업비 PV=수입 PV×20%+20,000원. 실제 분석 결과가 아닙니다.')
 cols=st.columns(4)
 cols[0].metric('예상 보험료 수입',fmt(income) if pd.notna(income) else '미입력')
 cols[1].metric('예상 보험금 지급',fmt(cur.expected_benefit_pv_krw))
 cols[2].metric('사업비 및 기타 비용',fmt(expense) if pd.notna(expense) else '미입력')
 cols[3].metric('예상 손익',fmt(cur.profit_npv_krw))
 if pd.notna(income) and pd.notna(expense):
  residual=income-cur.expected_benefit_pv_krw-expense
  if abs(residual-cur.profit_npv_krw)>2:st.warning('수입−보험금−비용과 입력된 손익이 일치하지 않습니다. 추가 비용·할인 기준과 결과표를 확인하세요.')
  fig=go.Figure(go.Waterfall(orientation='v',measure=['absolute','relative','relative','total'],x=['보험료 수입','보험금 지급','사업비 등','남는 금액'],y=[income,-cur.expected_benefit_pv_krw,-expense,0],text=[fmt(income),fmt(-cur.expected_benefit_pv_krw),fmt(-expense),fmt(residual)],textposition='outside',increasing=dict(marker_color='#008C82'),decreasing=dict(marker_color='#D18A70'),totals=dict(marker_color='#29425F')))
  fig.update_layout(height=420,yaxis_title='가입자 1인당 현재가치 (원)',showlegend=False,margin=dict(t=50))
  st.plotly_chart(fig,use_container_width=True)
 else:st.caption('수입·사업비 분석값이 아직 없어 수입·지출 그래프를 표시하지 않습니다. CSV에 해당 결과 열을 추가하면 자동 표시됩니다.')
 st.subheader('치료 이용이 늘어나면 손익은?')
 fig=go.Figure(go.Bar(x=['예상대로 이용','예상보다 많이 이용'],y=[pair.loc['기준'].profit_npv_krw,pair.loc['이용 증가'].profit_npv_krw],marker_color=['#29425F','#008C82'],text=[fmt(pair.loc['기준'].profit_npv_krw),fmt(pair.loc['이용 증가'].profit_npv_krw)],textposition='outside'))
 fig.add_hline(y=0,line_color='#8B99AA');fig.update_layout(height=330,yaxis_title='보험사 예상 손익 · 현재가치(원)',margin=dict(t=45))
 st.plotly_chart(fig,use_container_width=True)
 st.caption('양수는 이익, 음수는 손실입니다. 결과는 설정한 가정에서의 수지이며 판매 가능 여부나 지속 가능성을 판정하지 않습니다.')
 st.metric('예상 대비 보험금 지급 비율',f'{cur.benefit_ae:.0%}',help='100%는 처음 예상과 같고, 125%는 예상보다 지급액이 25% 많다는 뜻입니다.')
with st.expander('가상값 구성과 원래 분석 용어'):
 st.write('현재가치(PV)는 미래의 금액을 현재 시점 가치로 환산한 값입니다. 보험사 손익은 순현재가치(NPV), 예상 대비 지급 비율은 급부 A/E에 해당합니다.')
 st.write('기존 가상값을 유지했습니다. 예상 지급 횟수: 12회 한도 3.2회/24회 한도 4.4회, 180일 대기 0.9배. 보험금 PV=횟수×지급액×0.88. 연납 보험료=(기준 보험금 PV+20,000)/(0.8×8.5)를 100원 단위 반올림. 이용 증가 보험금은 12회 1.25배/24회 1.45배입니다. 실제 계리모형 결과가 아닙니다.')
 st.write('\n\n'.join(df.source_note.unique()))
st.download_button('현재 결과표 다운로드',df.drop(columns=['monthly','max_cover']).to_csv(index=False).encode('utf-8-sig'),'demo2_results.csv','text/csv')
