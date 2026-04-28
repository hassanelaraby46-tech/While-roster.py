import streamlit as st
import pandas as pd
from xlsxwriter.utility import xl_col_to_name
import calendar
import datetime
import io

# إعدادات الصفحة
st.set_page_config(page_title="Shift Distribution System", page_icon="📅")

st.title("📅 Shift Distribution System")
st.markdown("قم بإدخال أسماء الموظفين لتوليد جدول المناوبات تلقائياً لعام 2026.")

# --- مدخلات المستخدم ---
# تحديد الشهر والسنة تلقائياً أو يدوياً
now = datetime.datetime.now()
year = st.sidebar.number_input("Year", min_value=2024, max_value=2030, value=2026)
month = st.sidebar.selectbox("Month", range(1, 13), index=now.month - 1)

# إدخال الأسماء عبر نص مفصول بفاصلة أو سطر جديد
names_input = st.text_area("Enter Staff Names (Each name on a new line):", height=150)
names = [name.strip() for name in names_input.split('\n') if name.strip()]

if st.button("Generate Schedule"):
    if not names:
        st.error("Please enter at least one name!")
    else:
        # --- منطق توزيع المناوبات ---
        shifts = ['M', 'L', 'L', 'N', 'N', 'O', 'O']
        num_days = calendar.monthrange(year, month)[1] 
        days_list = [datetime.date(year, month, day).strftime("%d-%b") for day in range(1, num_days + 1)]
        day_names_list = [calendar.day_name[calendar.weekday(year, month, day)].lower() for day in range(1, num_days + 1)]

        data = []
        for i, name in enumerate(names):
            fair_shifts = [shifts[(k + i) % len(shifts)] for k in range(num_days)]
            for day_num, day_name, shift in zip(days_list, day_names_list, fair_shifts):
                data.append({'names': name, 'Date': day_num, 'day': day_name, 'shifts': shift})

        df = pd.DataFrame(data)
        df['names'] = pd.Categorical(df['names'], categories=names, ordered=True)
        df_H = df.pivot(index=['Date', 'day'], columns='names', values='shifts')

        # --- إنشاء ملف الإكسيل في الذاكرة (Memory buffer) ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_H.to_excel(writer, index=True, sheet_name='Schedule')
            workbook = writer.book
            worksheet = writer.sheets['Schedule']

            # تنسيقات
            format_M = workbook.add_format({'bg_color': '#CFE2F3', 'border': 1})
            format_L = workbook.add_format({'bg_color': '#FFF2CC', 'border': 1})
            format_N = workbook.add_format({'bg_color': '#F4CCCC', 'border': 1})
            format_O = workbook.add_format({'bg_color': '#D9EAD3', 'border': 1})
            friday_format = workbook.add_format({'bg_color': '#EAD1DC', 'bold': True, 'border': 1})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1, 'align': 'center'})

            last_col_idx = len(names) + 1
            last_col_letter = xl_col_to_name(last_col_idx)
            full_range = f'C2:{last_col_letter}{num_days + 1}'

            # تطبيق التنسيق الشرطي
            for val, fmt in [('M', format_M), ('L', format_L), ('N', format_N), ('O', format_O)]:
                worksheet.conditional_format(full_range, {'type': 'cell', 'criteria': '==', 'value': f'"{val}"', 'format': fmt})

            for row_idx, d_name in enumerate(day_names_list):
                if d_name == 'friday':
                    row_range = f'A{row_idx + 2}:{last_col_letter}{row_idx + 2}'
                    worksheet.conditional_format(row_range, {'type': 'no_blanks', 'format': friday_format})

            # صف المجموع
            total_row_idx = num_days + 1
            worksheet.write(total_row_idx, 0, 'TOTAL', header_format)
            worksheet.write(total_row_idx, 1, 'HOURS', header_format)
            for i, _ in enumerate(names):
                col_letter = xl_col_to_name(i + 2)
                formula = f'=(COUNTIF({col_letter}2:{col_letter}{num_days+1},"M")*6)+(COUNTIF({col_letter}2:{col_letter}{num_days+1},"L")*12)+(COUNTIF({col_letter}2:{col_letter}{num_days+1},"N")*12)'
                worksheet.write_formula(total_row_idx, i + 2, formula, header_format)

            worksheet.set_column('A:B', 12)
            worksheet.freeze_panes(1, 2)

        processed_data = output.getvalue()

        # --- عرض النتيجة وزر التحميل ---
        st.success("Schedule generated successfully!")
        st.dataframe(df_H) # عرض الجدول في الصفحة
        
        st.download_button(
            label="📥 Download Excel File",
            data=processed_data,
            file_name=f"Roster_{calendar.month_name[month]}_{year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
