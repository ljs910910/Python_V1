from docx import Document
from docx.shared import Inches
import re
import datetime

now = datetime.datetime.now()
now_dt = now.strftime('%Y-%m-%d')
result = re.sub('[^0-9]', '', now_dt)
print('today',result)

#document = Document('C:/Users/LG/Desktop/WEB3.0_플랫폼_운영보고서_20200909.docx')
document = Document('C:/Users/LG/Desktop/WEB3.0_플랫폼_운영보고서_' + result + '.docx')

file_list = ['C:/Users/LG/Desktop/WCS/qat/모니터링샘플데이터0819/capture/이미지 048.png',
             'C:/Users/LG/Desktop/WCS/qat/모니터링샘플데이터0819/capture/이미지 049.png']

file_list1 = ['C:/Users/LG/Desktop/WCS/qat/모니터링샘플데이터0819/capture/ocr대상/이미지 046.png',
              'C:/Users/LG/Desktop/WCS/qat/모니터링샘플데이터0819/capture/ocr대상/이미지 047.png']

tables = document.tables
num = 5

for i in file_list:
    p = tables[num].rows[0].cells[0].add_paragraph()
    r = p.add_run()
    r.add_picture(i, width=Inches(6.7))
    num +=1
    if num == 7:
        for k in file_list1:
            p = tables[num].rows[0].cells[0].add_paragraph()
            r = p.add_run()
            r.add_picture(k, width=Inches(6.7))
            num += 1
            if num == 9: break

document.save('C:/Users/LG/Desktop/WEB3.0_플랫폼_운영보고서_' + result + '.docx')
