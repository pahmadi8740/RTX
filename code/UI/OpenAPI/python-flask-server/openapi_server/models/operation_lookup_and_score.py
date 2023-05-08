# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from openapi_server.models.base_model_ import Model
from openapi_server.models.one_ofobjectobject import OneOfobjectobject
from openapi_server import util

from openapi_server.models.one_ofobjectobject import OneOfobjectobject  # noqa: E501

class OperationLookupAndScore(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, id=None, parameters=None, runner_parameters=None, unique=True):  # noqa: E501
        """OperationLookupAndScore - a model defined in OpenAPI

        :param id: The id of this OperationLookupAndScore.  # noqa: E501
        :type id: str
        :param parameters: The parameters of this OperationLookupAndScore.  # noqa: E501
        :type parameters: object
        :param runner_parameters: The runner_parameters of this OperationLookupAndScore.  # noqa: E501
        :type runner_parameters: OneOfobjectobject
        :param unique: The unique of this OperationLookupAndScore.  # noqa: E501
        :type unique: bool
        """
        self.openapi_types = {
            'id': str,
            'parameters': object,
            'runner_parameters': OneOfobjectobject,
            'unique': bool
        }

        self.attribute_map = {
            'id': 'id',
            'parameters': 'parameters',
            'runner_parameters': 'runner_parameters',
            'unique': 'unique'
        }

        self._id = id
        self._parameters = parameters
        self._runner_parameters = runner_parameters
        self._unique = unique

    @classmethod
    def from_dict(cls, dikt) -> 'OperationLookupAndScore':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The OperationLookupAndScore of this OperationLookupAndScore.  # noqa: E501
        :rtype: OperationLookupAndScore
        """
        return util.deserialize_model(dikt, cls)

    @property
    def id(self):
        """Gets the id of this OperationLookupAndScore.


        :return: The id of this OperationLookupAndScore.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id):
        """Sets the id of this OperationLookupAndScore.


        :param id: The id of this OperationLookupAndScore.
        :type id: str
        """
        allowed_values = ["lookup_and_score"]  # noqa: E501
        if id not in allowed_values:
            raise ValueError(
                "Invalid value for `id` ({0}), must be one of {1}"
                .format(id, allowed_values)
            )

        self._id = id

    @property
    def parameters(self):
        """Gets the parameters of this OperationLookupAndScore.


        :return: The parameters of this OperationLookupAndScore.
        :rtype: object
        """
        return self._parameters

    @parameters.setter
    def parameters(self, parameters):
        """Sets the parameters of this OperationLookupAndScore.


        :param parameters: The parameters of this OperationLookupAndScore.
        :type parameters: object
        """

        self._parameters = parameters

    @property
    def runner_parameters(self):
        """Gets the runner_parameters of this OperationLookupAndScore.


        :return: The runner_parameters of this OperationLookupAndScore.
        :rtype: OneOfobjectobject
        """
        return self._runner_parameters

    @runner_parameters.setter
    def runner_parameters(self, runner_parameters):
        """Sets the runner_parameters of this OperationLookupAndScore.


        :param runner_parameters: The runner_parameters of this OperationLookupAndScore.
        :type runner_parameters: OneOfobjectobject
        """

        self._runner_parameters = runner_parameters

    @property
    def unique(self):
        """Gets the unique of this OperationLookupAndScore.


        :return: The unique of this OperationLookupAndScore.
        :rtype: bool
        """
        return self._unique

    @unique.setter
    def unique(self, unique):
        """Sets the unique of this OperationLookupAndScore.


        :param unique: The unique of this OperationLookupAndScore.
        :type unique: bool
        """

        self._unique = unique
