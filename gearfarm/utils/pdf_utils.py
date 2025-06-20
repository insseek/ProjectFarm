# -*- coding: utf-8 -*-
import os
import uuid
import subprocess
# import fitz
import PyPDF2
import pdfplumber
from PyPDF2 import PdfFileReader, PdfFileWriter

from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTFigure


class PDFUtil(object):

    def search_text_page(self, pdf_path, search_value):
        '''
        搜索文本在pdf的第几页
        :param pdf_path:
        :param search_value:
        :return:
        '''
        page_nums = []
        with pdfplumber.open(pdf_path) as pdf_file:
            # 使用 PyPDF2 打开 PDF
            pdf_reader = PyPDF2.PdfFileReader(open(pdf_path, "rb"))
            page_count = pdf_reader.getNumPages()
            # len(pdf.pages)为PDF文档页数，一页页解析
            for i in range(page_count):
                # pdf.pages[i] 是读取PDF文档第i+1页
                page = pdf_file.pages[i]
                # page.extract_text()函数即读取文本内容
                page_content = page.extract_text()
                if search_value in page_content:
                    page_nums.append(i)
        return page_nums

    def extract_text(self, pdf_path):
        '''
        提取文本
        :param pdf_path:
        :param text:
        :return:
        '''

        result = {}
        with pdfplumber.open(pdf_path) as pdf_file:
            # 使用 PyPDF2 打开 PDF
            pdf_reader = PyPDF2.PdfFileReader(open(pdf_path, "rb"))
            page_count = pdf_reader.getNumPages()
            # len(pdf.pages)为PDF文档页数，一页页解析
            for i in range(page_count):
                # pdf.pages[i] 是读取PDF文档第i+1页
                page = pdf_file.pages[i]
                # page.extract_text()函数即读取文本内容
                page_content = page.extract_text()
                result[i] = page_content
        return result

    #
    # def pdf_to_image(self, pdf_path, image_dir, page_number=None):
    #     '''
    #     pdf转化成图片，可以指定某一页
    #     :param pdf_path:
    #     :param image_dir:
    #     :param page_number:
    #     :return:
    #     '''
    #     print("imagePath=" + image_dir)
    #     pdf_doc = fitz.open(pdf_path)
    #     if page_number is not None:
    #         if page_number <= pdf_doc.pageCount:
    #             self.pdf_page_to_image(pdf_path, page_number, image_dir)
    #     else:
    #         for page_number in range(pdf_doc.pageCount):
    #             self.pdf_page_to_image(pdf_path, page_number, image_dir)
    #
    # def pdf_page_to_image(self, pdf_path, page_number, image_dir):
    #     # pdf的某一页转化成图片
    #     pdf_doc = fitz.open(pdf_path)
    #     page = pdf_doc[page_number]
    #     rotate = int(0)
    #     # 每个尺寸的缩放系数为1.3，这将为我们生成分辨率提高2.6的图像。
    #     # 此处若是不做设置，默认图片大小为：792X612, dpi=96
    #     zoom_x = 1.33333333  # (1.33333333-->1056x816)   (2-->1584x1224)
    #     zoom_y = 1.33333333
    #     mat = fitz.Matrix(zoom_x, zoom_y).preRotate(rotate)
    #     pix = page.getPixmap(matrix=mat, alpha=False)
    #     if not os.path.exists(image_dir):  # 判断存放图片的文件夹是否存在
    #         os.makedirs(image_dir)  # 若图片文件夹不存在就创建
    #     path = image_dir + '/' + 'images_%s.png' % page_number
    #     pix.writePNG(path)  # 将图片写入指定的文件夹内
    #     return path

    def parse_layout(self, layout, search_value):
        """
        获取文本的坐标
        Function to recursively parse the layout tree.
        """
        data = []
        for lt_obj in layout:
            # print(lt_obj.__class__.__name__)
            # 猜测bbox (x1,y1, x2, y2)   x1,y1为左下角   x2, y2为右上角
            if isinstance(lt_obj, LTTextBox) or isinstance(lt_obj, LTTextLine):
                text = lt_obj.get_text()
                if search_value in text:
                    data.append({
                        "text": text,
                        "bbox": lt_obj.bbox
                    })
            elif isinstance(lt_obj, LTFigure):
                self.parse_layout(lt_obj, search_value)  # Recursive
        return data

    def search_text_boxes(self, pdf_path, search_value):
        fp = open(pdf_path, 'rb')
        parser = PDFParser(fp)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        result = []
        for page_index, page in enumerate(PDFPage.create_pages(doc)):
            interpreter.process_page(page)
            layout = device.get_result()
            data = self.parse_layout(layout, search_value)
            if data:
                result.append({
                    "page": page_index + 1,
                    "boxes": data
                })
        return result

    def search_text_boxes_position_y(self, pdf_path, search_value):
        fp = open(pdf_path, 'rb')
        parser = PDFParser(fp)
        doc = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        result = []
        for page_index, page in enumerate(PDFPage.create_pages(doc)):
            interpreter.process_page(page)
            layout = device.get_result()
            boxes = self.parse_layout(layout, search_value)
            if boxes:
                for box in boxes:
                    box_text = box['text']
                    text_lines = box_text.split('\n')
                    lines_len = len(text_lines)
                    line_num = 0
                    for index, i in enumerate(text_lines):
                        if search_value in i:
                            line_num = index
                            break
                    x1, y1, x2, y2 = box['bbox']
                    # 从上往下数
                    if line_num < lines_len / 2:
                        y = y2 - (y2 - y1) / lines_len * line_num
                    else:
                        y = y1 + (y2 - y1) / lines_len * (lines_len - line_num)
                    box['position_y'] = y
                result.append({
                    "page": page_index + 1,
                    "boxes": boxes
                })
        return result

    def convert_html_to_pdf(self, link, dir_path, compress=True):
        '''
        读取html页面转化为pdf
        :param link:
        :param dir_path:
         :param compress:
        :return:
        '''
        uid = str(uuid.uuid4()).replace('-', '')
        # 判断存放的文件夹是否存在 不存在就创建
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        temp_path_1 = '{}/temp-{}_1.pdf'.format(dir_path, uid)
        temp_path_2 = '{}/temp_{}_2.pdf'.format(dir_path, uid)
        out_path = '{}/{}.pdf'.format(dir_path, uid)

        # 依赖应用Prince GhostScript
        subprocess.call(['prince', link, '--javascript',
                         '--no-embed-fonts', '--no-artificial-fonts', '-o', temp_path_1])
        with open(temp_path_1, 'rb') as input_file:
            pdf = PdfFileReader(input_file)
            writer = PdfFileWriter()
            writer.addPage(pdf.getPage(0))
            writer.removeLinks()
            if pdf.getNumPages() > 0:
                for i in range(1, pdf.getNumPages()):
                    writer.addPage(pdf.getPage(i))
            # 压缩
            if compress:
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

#
# def test():
#     pdf_path = '/Users/inseeker/Documents/chilun-projects/farm-backend/30_contract_preview_signed.pdf'
#     pdf_utils = PDFUtil()
#     result = pdf_utils.search_text_boxes_position_y(pdf_path, '乙方（签字或盖章）')
#     print(result)
#
# def find_sign_location(file_path, search_value):
#     """
#     获取指定文字在pdf中的页码和坐标
#     """
#     pdf_util = PDFUtil()
#     data = pdf_util.search_text_boxes_position_y(file_path, search_value)
#     if data:
#         page_data = data[0]
#         page_index = page_data['page']
#         position_y = page_data['boxes'][0]['position_y']
#         print(page_index, position_y)
#         return page_index, position_y
#
# find_sign_location('/Users/inseeker/Documents/chilun-projects/farm-backend/30_contract_preview_signed.pdf', "乙方（签字或盖章）")
