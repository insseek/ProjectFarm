import os.path
import subprocess

from django.urls import reverse
from django.conf import settings
from PyPDF2 import PdfFileReader, PdfFileWriter


def report_path(report_id):
    return '{}.pdf'.format(settings.MEDIA_ROOT + report_id)


def report_url(request, report_id):
    protocol = 'https' if request.is_secure() else 'http'
    report_url =  reverse('reports:view', args=(report_id,))
    return protocol + "://" + request.get_host() + report_url


def gen(request, report_id):
    temp_path_1 = '{}temp-{}-1.pdf'.format(settings.MEDIA_ROOT, report_id)
    temp_path_2 = '{}temp-{}-2.pdf'.format(settings.MEDIA_ROOT, report_id)
    out_path = report_path(report_id)

    # 依赖应用Prince GhostScript
    subprocess.call(['prince', report_url(request, report_id), '--javascript',
                     '--no-embed-fonts', '--no-artificial-fonts', '-o', temp_path_1])
    with open(temp_path_1, 'rb') as input_file:
        pdf = PdfFileReader(input_file)
        writer = PdfFileWriter()
        writer.addPage(pdf.getPage(0))
        writer.removeLinks()
        if pdf.getNumPages() > 0:
            for i in range(1, pdf.getNumPages()):
                writer.addPage(pdf.getPage(i))
        if settings.COMPRESS_PDF:
            with open(temp_path_2, 'wb') as temp_output_file:
                writer.write(temp_output_file)
            subprocess.call(['gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4', '-dPDFSETTINGS=/printer',
                             '-dNOPAUSE', '-dQUIET', '-dBATCH', '-dColorConversionStrategy=/LeaveColorUnchanged',
                             '-sOutputFile=' + out_path, temp_path_2])
        else:
            with open(out_path, 'wb') as output_file:
                writer.write(output_file)
    if os.path.exists(temp_path_2):
        os.remove(temp_path_2)
    if os.path.exists(temp_path_1):
        os.remove(temp_path_1)
    return out_path
