import pandas as pd
import sys
import os
import plotly.express as px
import plotly.graph_objects as go
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.config import PROCESSED

OUTPUT = "charts"
os.makedirs(OUTPUT, exist_ok=True)

# LOAD DATA (With Column Normalization)

def load_data():
    files = files = sorted([f for f in os.listdir(PROCESSED) if f.endswith(".csv")])
    all_data = []

    for file in files:
        path = os.path.join(PROCESSED, file)
        df = pd.read_csv(path)

        # fix column names and case
        df.columns = [c.strip().replace('_', ' ').title() for c in df.columns]
        
        # rename column name ATM
        df = df.rename(columns={
            'Atm Name': 'ATM Name',
            'No Of XYZ Card Withdrawals': 'No Of XYZ Card Withdrawals'
        })
        
        print(f"Loaded {file}. Columns found: {list(df.columns)}")
        all_data.append(df)

    full_df = pd.concat(all_data, ignore_index=True)
    return full_df

def preprocess(df):
    df['Date'] = pd.to_datetime(df['Date'])
    month_order = ["Jan","Feb","Mar","Apr","May","Jun"]
    
    df['Month'] = pd.Categorical(
        df['Date'].dt.strftime('%b'),
        categories=month_order,
        ordered=True
    )

    df['Year'] = df['Date'].dt.year
    df['Week'] = df['Date'].dt.isocalendar().week
    df['Weekday'] = df['Weekday'].str.strip().str.title()

    return df


# ANALYSIS & CHARTS

def save_yearly_charts(df, year):
    
    cols = df.columns
    total_withdrawals_col = 'No Of Withdrawals'
    total_amount_col = 'Total Amount Withdrawn'

    # 1. ATM EFFICIENCY (Transaction Size)
    if total_amount_col in cols and total_withdrawals_col in cols:
        # Avoid division by zero
        safe_df = df[df[total_withdrawals_col] > 0].copy()
        safe_df['Avg_Txn_Size'] = safe_df[total_amount_col] / safe_df[total_withdrawals_col]
        
        avg_size = safe_df.groupby('Month')['Avg_Txn_Size'].mean().reindex(["Jan", "Feb", "Mar", "Apr", "May", "Jun"])
        fig = px.line(
            x=avg_size.index,
            y=avg_size.values,
            markers=True,
            title=f"ATM Efficiency: Avg Withdrawal Size - {year} (Jan-Jun)",
            labels={"x": "Month", "y": "Avg Transaction Size"}
        )

        fig.update_layout(hovermode="x unified")
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Value: %{y:,}")
        fig.write_html(os.path.join(OUTPUT, f"efficiency_{year}.html"))

    # 2. WORKING DAY ANALYSIS
    if 'Working Day' in cols:
        # Grouping by Working Day (Usually 0 for holiday/weekend, 1 for workday)
        workday_avg = df.groupby('Working Day')[total_withdrawals_col].mean()
        # Attempt to label index if it's numeric
        if all(x in workday_avg.index for x in [0, 1]):
            workday_avg.index = ['Holiday/Weekend', 'Working Day']
        
        fig = px.bar(
            x=workday_avg.index,
            y=workday_avg.values,
            title=f"Average Daily Withdrawals: Work Day vs Holiday - {year}",
            labels={"x": "Day Type", "y": "Avg Withdrawals"}
        )

        fig.update_layout(hovermode="x unified")
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Value: %{y:,}")
        fig.write_html(os.path.join(OUTPUT, f"workday_impact_{year}.html"))

    # 3. FESTIVAL ANALYSIS
    if 'Festival Religion' in cols:
        # Filter out rows where no festival is occurring (e.g., 'None', 'No Festival', or empty)
        fest_df = df[~df['Festival Religion'].isin(['None', 'no_festival', 'No Festival', ' '])].copy()
        
        if not fest_df.empty:
            fest_impact = fest_df.groupby('Festival Religion')[total_amount_col].sum().sort_values()
            fig = px.bar(
                fest_impact,
                x=fest_impact.values,
                y=fest_impact.index,
                orientation='h',
                title=f"Total Amount Withdrawn per Festival - {year}",
                labels={"x": "Total Amount", "y": "Festival"}
            )

            fig.update_layout(hovermode="x unified")
            fig.update_traces(hovertemplate="<b>%{x}</b><br>Total Amount: %{y:,}")
            fig.write_html(os.path.join(OUTPUT, f"festival_impact_{year}.html"))
        else:
            print(f"No active festivals found in Jan-Jun {year} data.")

    target_col = next((c for c in cols if 'Withdrawals' in c and 'XYZ' not in c and 'Other' not in c), cols[0])
    xyz_col = next((c for c in cols if 'Xyz' in c), None)
    other_col = next((c for c in cols if 'Other' in c), None)
    # monthly (Jan-Jun)
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    
    monthly = df.groupby('Month')[target_col].sum().reindex(month_order)
    fig = px.bar(
        monthly,
        x=monthly.index,
        y=monthly.values,
        title=f"Monthly Transactions - {year} (Jan-Jun)",
        labels={"x": "Month", "y": "Total Withdrawals"}
    )

    fig.update_layout(hovermode="x unified")
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Value: %{y:,}")
    fig.write_html(os.path.join(OUTPUT, f"monthly_{year}.html"))

    # weekly
    weekly = df.groupby('Week')[target_col].sum().sort_index()
    weekly = weekly[weekly.index <= 27]
    fig = px.line(
        x=weekly.index,
        y=weekly.values,
        markers=True,
        title=f"Weekly Transactions - {year}",
        labels={"x": "Week", "y": "Total Withdrawals"}
    )

    fig.update_layout(hovermode="x unified")
    fig.update_traces(hovertemplate="Week %{x}<br>Withdrawals: %{y:,}")
    fig.write_html(os.path.join(OUTPUT, f"weekly_{year}.html"))

    # ATM Analysis 
    if 'ATM Name' in df.columns:
        atm = df.groupby('ATM Name')[target_col].sum().sort_values(ascending=False).head()
        atm_df = atm.reset_index()
        atm_df.columns = ["ATM Name","Total Withdrawals"]

        fig = px.bar(
            atm_df,
            x="ATM Name",
            y="Total Withdrawals",
            title=f"Top 5 ATMs - {year}"
        )
        fig.update_layout(hovermode="x unified")
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Value: %{y:,}")
        fig.write_html(os.path.join(OUTPUT, f"atm_{year}.html"))

    else:
        print(f"Skipping ATM chart for {year}: 'ATM Name' column not found.")

    # CARD TYPE ANALYSIS
    if xyz_col and other_col:
        xyz_total = df[xyz_col].sum()
        other_total = df[other_col].sum()
        
        card_series = pd.Series({'XYZ Card': xyz_total, 'Other Cards': other_total})
        fig = px.bar(
            x=card_series.index,
            y=card_series.values,
            title=f"Card Usage Comparison - {year}",
            labels={"x": "Card Type", "y": "Total Withdrawals"}
        )

        fig.update_layout(hovermode="x unified")
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Value: %{y:,}")
        fig.write_html(os.path.join(OUTPUT, f"card_comparison_{year}.html"))
    else:
        print(f"Skipping Card Chart for {year}: Could not find XYZ or Other columns.")

def monthly_growth_chart(df):

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]

    # Pivot table for comparison
    pivot = df.pivot_table(
        values='No Of Withdrawals',
        index='Month',
        columns='Year',
        aggfunc='sum'
    ).reindex(month_order)

    fig = px.bar(
        pivot,
        x=pivot.index,
        y=pivot.columns,
        barmode="group",
        title="Monthly ATM Withdrawal Growth Comparison (Jan–Jun)",
        labels={"value": "Withdrawals", "Month": "Month"}
    )

    fig.update_layout(hovermode="x unified")
    fig.update_traces(hovertemplate="Month: %{x}<br>Withdrawals: %{y:,}")
    fig.write_html(os.path.join(OUTPUT, "monthly_growth_comparison.html"))

def main():
    df = load_data()
    df = preprocess(df)

    # Analyse by Month (Jan-Jun)
    target_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    df = df[df['Month'].isin(target_months)]
    
    # Filter by Week (1 to 27)
    df = df[df['Week'] <= 27]

    monthly_growth_chart(df)

    available_years = sorted(df['Year'].unique())
    
    for year in available_years:
        year_df = df[df['Year'] == year].copy()
        if not year_df.empty:
            save_yearly_charts(year_df, year)
            print(f"Generated charts for {year}")