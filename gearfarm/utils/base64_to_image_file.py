import base64
import binascii
import imghdr
import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile


class Base64ToImageFile(object):
    """
    A django-rest-framework field for handling image-uploads through raw post data.
    It uses base64 for en-/decoding the contents of the file.
    """
    ALLOWED_TYPES = (
        "jpeg",
        "jpg",
        "png",
        "gif"
    )
    EMPTY_VALUES = (None, '', [], (), {})
    INVALID_FILE_MESSAGE = "Please upload a valid image."
    INVALID_TYPE_MESSAGE = "The type of the image couldn't be determined."

    def to_file(self, base64_data):
        # Check if this is a base64 string
        if base64_data in self.EMPTY_VALUES:
            return None
        if isinstance(base64_data, str):
            # Strip base64 header.
            if ';base64,' in base64_data:
                header, base64_data = base64_data.split(';base64,')

            # Try to decode the file. Return validation error if it fails.
            try:
                decoded_file = base64.b64decode(base64_data)
            except (TypeError, binascii.Error, ValueError):
                raise ValidationError(self.INVALID_FILE_MESSAGE)
            # Generate file name:
            file_name = self.get_file_name(decoded_file)
            # Get the file name extension:
            file_extension = self.get_file_extension(file_name, decoded_file)
            if file_extension not in self.ALLOWED_TYPES:
                raise ValidationError(self.INVALID_TYPE_MESSAGE)
            complete_file_name = file_name + "." + file_extension
            data = ContentFile(decoded_file, name=complete_file_name)
            return data
        raise ValidationError('Invalid type. This is not an base64 string: {}'.format(
            type(base64_data)))

    def get_file_name(self, decoded_file):
        return str(uuid.uuid4())

    def get_file_extension(self, filename, decoded_file):
        try:
            from PIL import Image
        except ImportError:
            raise ImportError("Pillow is not installed.")
        extension = imghdr.what(filename, decoded_file)

        # Try with PIL as fallback if format not detected due
        # to bug in imghdr https://bugs.python.org/issue16512
        if extension is None:
            try:
                image = Image.open(io.BytesIO(decoded_file))
            except (OSError, IOError):
                raise ValidationError(self.INVALID_FILE_MESSAGE)

            extension = image.format.lower()

        extension = "jpg" if extension == "jpeg" else extension
        return extension


def base64_string_to_file(base64_string):
    return Base64ToImageFile().to_file(base64_string)
