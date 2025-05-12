import streamlit as st
import pandas as pd
import pydeck as pdk
import numpy as np

# -------------------- 데이터 로드 --------------------
@st.cache_data
def load_data():
    df = pd.read_excel("earthquake_data_2020_2025.xlsx", skiprows=2)
    df.columns = ['번호', '발생시각', '규모', '깊이(km)', '최대진도', '위도', '경도', '위치', '지도', '상세정보']
    df = df.dropna(subset=['발생시각', '규모', '위도', '경도'])
    df['위도'] = df['위도'].str.replace(' N', '', regex=False).astype(float)
    df['경도'] = df['경도'].str.replace(' E', '', regex=False).astype(float)
    df['발생시각'] = pd.to_datetime(df['발생시각'])
    df['규모'] = df['규모'].astype(float)
    df['깊이(km)'] = df['깊이(km)'].replace('-', np.nan).astype(float)
    df['시간대'] = df['발생시각'].dt.hour
    df['광역시도'] = df['위치'].str.extract(r'^(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)')
    return df

df = load_data()

# -------------------- UI --------------------
st.title("🌏 국내 지진 발생 시각화 대시보드 (2020-2025)")

# 날짜 필터
date_range = st.date_input("지진 발생일 범위", [df['발생시각'].min().date(), df['발생시각'].max().date()])

# 지역 필터
광역시도_목록 = sorted(df['광역시도'].dropna().unique())
selected_regions = st.multiselect("📍 광역시/도 선택", 광역시도_목록)

# 지진 규모 필터
min_mag, max_mag = float(df['규모'].min()), float(df['규모'].max())
mag_range = st.slider("지진 규모 범위 선택", min_value=min_mag, max_value=max_mag, value=(min_mag, max_mag))

# -------------------- 필터링 --------------------
filtered = df[
    (df['발생시각'].dt.date >= date_range[0]) &
    (df['발생시각'].dt.date <= date_range[1]) &
    (df['규모'] >= mag_range[0]) & (df['규모'] <= mag_range[1])
]

if selected_regions:
    filtered = filtered[filtered['광역시도'].isin(selected_regions)]

# -------------------- 요약 통계 --------------------
st.subheader("📌 지진 정보 요약")
col1, col2, col3 = st.columns(3)
if not filtered.empty:
    col1.metric("최대 규모", f"{filtered['규모'].max():.1f}")
    col2.metric("평균 규모", f"{filtered['규모'].mean():.2f}")
    col3.metric("발생 건수", len(filtered))

    top_region = filtered['광역시도'].value_counts().idxmax()
    st.markdown(f"📍 **가장 많이 발생한 지역:** {top_region}")
else:
    st.warning("선택한 조건에 해당하는 지진 데이터가 없습니다.")

# -------------------- 규모 변화 라인 차트 --------------------
st.subheader("📈 지진 규모 변화 추이")
if not filtered.empty:
    line_data = filtered.sort_values("발생시각")[['발생시각', '규모']]
    st.line_chart(line_data.rename(columns={'발생시각': 'index'}).set_index('index'))

# -------------------- 지도 시각화 --------------------
st.subheader("🗺 지도에서 지진 발생 위치 보기")
if not filtered.empty:
    map_data = filtered.rename(columns={'위도': 'latitude', '경도': 'longitude'})
    map_data['발생시각'] = map_data['발생시각'].dt.strftime('%Y-%m-%d %H:%M')

    def depth_to_color(depth):
        if pd.isna(depth):
            return [200, 200, 200, 100]
        elif depth <= 5:
            return [0, 255, 0, 140]
        elif depth <= 15:
            return [255, 165, 0, 140]
        else:
            return [255, 0, 0, 160]

    map_data['color'] = map_data['깊이(km)'].apply(depth_to_color)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_data,
        get_position='[longitude, latitude]',
        get_radius='규모 * 10000',
        get_fill_color='color',
        pickable=True
    )

    view_state = pdk.ViewState(
        latitude=map_data['latitude'].mean(),
        longitude=map_data['longitude'].mean(),
        zoom=6
    )

    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=[layer],
        tooltip={"text": "📍 {위치}\n규모: {규모}\n깊이: {깊이(km)}km\n🕒 {발생시각}"}
    ))
