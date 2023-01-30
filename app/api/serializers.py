from rest_framework import serializers
from .helper import process_base64_image, process_base64_file
import six


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        # Check if this is a base64 string
        if isinstance(data, six.string_types):
            data = process_base64_image(data, self.fail)

        return super(Base64ImageField, self).to_internal_value(data)


class Base64FileField(serializers.FileField):
    def to_internal_value(self, data):
        # Check if this is a base64 string
        # if isinstance(data, six.string_types):
        data = process_base64_file(data, self.fail)

        return super(Base64FileField, self).to_internal_value(data)
