from io import BytesIO
from PIL import Image


class PDFConverter:
     def convert_images(self, bytes_of_images: list) -> BytesIO:
        images = []
        for i in bytes_of_images:
            bio = BytesIO(i)
            images.append(Image.open(bio))

        res_byte_arr = BytesIO()
        images[0].save(res_byte_arr, "PDF", resolution=100.0, save_all=True, append_images=images[1:])

        return res_byte_arr
