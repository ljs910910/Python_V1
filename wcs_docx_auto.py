from docx import Document
from docx.shared import Inches
import docx
import re
import datetime

def now_date():
    now = datetime.datetime.now()
    now_dt = now.strftime('%Y-%m-%d')
    result = re.sub('[^0-9]', '', now_dt)
    print('today',result)
    return result

try:
    #document = Document('C:/Users/LG/Desktop/WEB3.0_플랫폼_운영보고서_20200909.docx')
    document = Document('C:/Users/webiznet/Desktop/Olleh_TV_홈포털_플랫폼_운영보고서_' + now_date() + '.docx')

    file_list = ['C:/Users/webiznet/Desktop/QAT_sample/수요일_정기점검_모니터링샘플데이터0819/capture/이미지 048.png',
                 'C:/Users/webiznet/Desktop/QAT_sample/수요일_정기점검_모니터링샘플데이터0819/capture/이미지 049.png']
    file_list1 = ['C:/Users/webiznet/Desktop/QAT_sample/수요일_정기점검_모니터링샘플데이터0819/capture/ocr대상/이미지 046.png',
                  'C:/Users/webiznet/Desktop/QAT_sample/수요일_정기점검_모니터링샘플데이터0819/capture/ocr대상/이미지 047.png']

    tables = document.tables
    num = 6
    for i in file_list:
        p = tables[num].rows[0].cells[0].add_paragraph()
        r = p.add_run()
        r.add_picture(i, width=Inches(6.7))
        num +=1
        if num == 8:
            for k in file_list1:
                p = tables[num].rows[0].cells[0].add_paragraph()
                r = p.add_run()
                r.add_picture(k, width=Inches(6.7))
                num += 1
                if num == 10: break
    document.save('C:/Users/webiznet/Desktop/Olleh_TV_홈포털_플랫폼_운영보고서_' + now_date() + '.docx')

except NameError as e:
    print('Error', e)

except docx.opc.exceptions.PackageNotFoundError as e:
    print('Error', e)
