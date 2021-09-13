# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from openapi_server.models.base_model_ import Model
from openapi_server import util


class OperationFilterKgraph(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, id=None, parameters=None):  # noqa: E501
        """OperationFilterKgraph - a model defined in OpenAPI

        :param id: The id of this OperationFilterKgraph.  # noqa: E501
        :type id: str
        :param parameters: The parameters of this OperationFilterKgraph.  # noqa: E501
        :type parameters: object
        """
        self.openapi_types = {
            'id': str,
            'parameters': object
        }

        self.attribute_map = {
            'id': 'id',
            'parameters': 'parameters'
        }

        self._id = id
        self._parameters = parameters

    @classmethod
    def from_dict(cls, dikt) -> 'OperationFilterKgraph':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The OperationFilterKgraph of this OperationFilterKgraph.  # noqa: E501
        :rtype: OperationFilterKgraph
        """
        return util.deserialize_model(dikt, cls)

    @property
    def id(self):
        """Gets the id of this OperationFilterKgraph.


        :return: The id of this OperationFilterKgraph.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id):
        """Sets the id of this OperationFilterKgraph.


        :param id: The id of this OperationFilterKgraph.
        :type id: str
        """
        allowed_values = ["filter_kgraph"]  # noqa: E501
        if id not in allowed_values:
            raise ValueError(
                "Invalid value for `id` ({0}), must be one of {1}"
                .format(id, allowed_values)
            )

        self._id = id

    @property
    def parameters(self):
        """Gets the parameters of this OperationFilterKgraph.


        :return: The parameters of this OperationFilterKgraph.
        :rtype: object
        """
        return self._parameters

    @parameters.setter
    def parameters(self, parameters):
        """Sets the parameters of this OperationFilterKgraph.


        :param parameters: The parameters of this OperationFilterKgraph.
        :type parameters: object
        """

        self._parameters = parameters
