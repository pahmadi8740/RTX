import connexion
import six

from openapi_server import util
from ARAX_query_tracker import ARAXQueryTracker


def get_status(last_n_hours=None, id_=None):  # noqa: E501
    """Obtain status information about the endpoint

     # noqa: E501

    :param last_n_hours: Limit results to the past N hours
    :type last_n_hours: int
    :param id: Identifier of the log entry
    :type id: int

    :rtype: object
    """

    query_tracker = ARAXQueryTracker()
    status = query_tracker.get_status(last_n_hours=last_n_hours, id_=id_)
    return status