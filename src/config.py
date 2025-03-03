# Copyright © 2021-2025 Geospatial Research Institute Toi Hangarau
# LICENSE: https://github.com/GeospatialResearch/Digital-Twins/blob/master/LICENSE
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Collection of utils that are used for system and environment configuration."""

import os
import pathlib
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
load_dotenv("api_keys.env")


def _get_env_variable(var_name: str, default: Optional[str] = None, allow_empty: bool = False) -> str:
    """
    Read a string environment variable, with settings to allow defaults, empty values.
    To read a boolean use _get_bool_env_variable.

    For public use please use EnvVariable.

    Parameters
    ----------
    var_name : str
        The name of the environment variable to retrieve.
    default : Optional[str] = None
        Default return value if the environment variable is empty or does not exist.
    allow_empty : bool
        If False then a KeyError will be raised if the environment variable is empty.

    Returns
    -------
    str
        The environment variable, or default if it is empty or does not exist.

    Raises
    ------
    KeyError
        If allow_empty is False and the environment variable is empty string or None
    """
    env_var = os.getenv(var_name)
    if default is not None and env_var in (None, ""):
        # Set env_var to default, but do not override empty str with None
        env_var = default
    if not allow_empty and env_var in (None, ""):
        raise KeyError(f"Environment variable {var_name} not set, and allow_empty is False")
    return env_var


def _get_bool_env_variable(var_name: str, default: Optional[bool] = None) -> bool:
    """
    Read an environment variable and attempts to cast to bool, with settings to allow defaults.
    For bool casting we have the problem where bool("False") == True
    but this function fixes that so get_bool_env_variable("False") == False

    For public use please use EnvVariable.

    Parameters
    ----------
    var_name : str
        The name of the environment variable to retrieve.
    default : Optional[bool] = None
        Default return value if the environment variable does not exist.

    Returns
    -------
    bool
        The environment variable, or default if it does not exist

    Raises
    ------
    ValueError
        If allow_empty is False and the environment variable is empty string or None
    """
    env_variable = _get_env_variable(var_name, str(default))
    try:
        return cast_str_to_bool(env_variable)
    except ValueError as e:
        raise ValueError(f"Environment variable {var_name}={env_variable}"
                         f" cannot be cast to bool due to ValueError.") from e


def cast_str_to_bool(string: str) -> bool:
    """
    Attempt to cast a str to bool.
    For bool casting we have the problem where bool("False") == True
    but this function fixes that so cast_str_to_bool("False") == False

    Parameters
    ----------
    string : str
        The string to be cast to bool.

    Returns
    -------
    bool
        The interpreted value of the string.

    Raises
    ------
    ValueError
        If the string cannot be cast to bool.
    """
    truth_values = {"true", "t", "1"}
    false_values = {"false", "f", "0"}
    if string.lower() in truth_values:
        return True
    elif string.lower() in false_values:
        return False
    raise ValueError(f"String {string} being casted to bool but is not in {truth_values} or {false_values}")


class EnvVariable:  # pylint: disable=too-few-public-methods
    """Encapsulates all environment variable fetching, ensuring proper defaults and types."""

    STATSNZ_API_KEY = _get_env_variable("STATSNZ_API_KEY")
    LINZ_API_KEY = _get_env_variable("LINZ_API_KEY")
    MFE_API_KEY = _get_env_variable("MFE_API_KEY")
    NIWA_API_KEY = _get_env_variable("NIWA_API_KEY")

    DEBUG_TRACEBACK = _get_bool_env_variable("DEBUG_TRACEBACK", default=False)
    TEST_DATABASE_INTEGRATION = _get_bool_env_variable("TEST_DATABASE_INTEGRATION", default=True)

    DATA_DIR = pathlib.Path(_get_env_variable("DATA_DIR"))
    DATA_DIR_MODEL_OUTPUT = pathlib.Path(_get_env_variable("DATA_DIR_MODEL_OUTPUT"))
    DATA_DIR_GEOSERVER = pathlib.Path(_get_env_variable("DATA_DIR_GEOSERVER"))
    FLOOD_MODEL_DIR = pathlib.Path(_get_env_variable("FLOOD_MODEL_DIR"))

    POSTGRES_HOST = _get_env_variable("POSTGRES_HOST", default="localhost")
    POSTGRES_PORT = _get_env_variable("POSTGRES_PORT", default="5431")
    POSTGRES_DB = _get_env_variable("POSTGRES_DB", default="db")
    POSTGRES_USER = _get_env_variable("POSTGRES_USER", default="postgres")
    POSTGRES_PASSWORD = _get_env_variable("POSTGRES_PASSWORD")

    MESSAGE_BROKER_HOST = _get_env_variable("MESSAGE_BROKER_HOST", default="localhost")

    GEOSERVER_HOST = _get_env_variable("GEOSERVER_HOST", default="http://localhost")
    GEOSERVER_PORT = _get_env_variable("GEOSERVER_PORT", default="8088")
    GEOSERVER_INTERNAL_HOST = _get_env_variable("GEOSERVER_INTERNAL_HOST", default=GEOSERVER_HOST)
    GEOSERVER_INTERNAL_PORT = _get_env_variable("GEOSERVER_INTERNAL_PORT", default=GEOSERVER_PORT)
    GEOSERVER_ADMIN_NAME = _get_env_variable("GEOSERVER_ADMIN_NAME", default="admin")
    GEOSERVER_ADMIN_PASSWORD = _get_env_variable("GEOSERVER_ADMIN_PASSWORD", default="geoserver")

    # NewZealidar config that we must ensure have values.
    _LIDAR_DIR = _get_env_variable("LIDAR_DIR")
    _DEM_DIR = _get_env_variable("DEM_DIR")
    _LAND_FILE = _get_env_variable("LAND_FILE", allow_empty=True)
    _INSTRUCTIONS_FILE = _get_env_variable("INSTRUCTIONS_FILE")
