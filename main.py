import sys
import pdb

sys.path.insert(0, "package")

import json
import os
import time
from datetime import datetime, timedelta


import pandas as pd
from bson.json_util import dumps
from dotenv import load_dotenv
import psutil
from s3 import S3
from database import Database

load_dotenv()


class FileOperation:

    # Defining class constants
    DATE_FORMAT_OF_JSON_FILE = "%Y-%m-%d %H:%M:%S.%f"
    TIME_STAMP_FOR_DATA = "%Y%m%d%H%M%S"
    TIME_STAMP_WEEKLY_DATA = "%d_%B_%Y_%H%M%S%f"
    BASE_PATH = os.getenv("BASE_PATH")
    JSON_FILE_NAME = os.getenv("FILENAME")

    def __init__(self):
        """
            Constructor for FileOperation class, initializing and defining
            variables.
        """

        self.db = Database()  # database object
        self.s3 = S3()  # s3 object
        print(FileOperation.BASE_PATH)
        if not os.path.isdir(FileOperation.BASE_PATH):
            os.makedirs(FileOperation.BASE_PATH)

        self.json_file_path = os.path.join(
            "/", os.getenv("BACKUP_JSON_PATH"), os.getenv("FILENAME")
        )

        # downloading last backup json from s3 for first time
        self.s3.download_json_date(FileOperation.JSON_FILE_NAME, self.json_file_path)

        self.start_of_week, self.end_of_week = self._get_start_date()

    def _get_start_date(self):
        """
        getting start date from lastbackupdate file if exist else getting
        initial date from database.
        """
        last_backup_date = self._get_last_backup_date()

        if last_backup_date:  #
            # getting backup date from s3
            start_date = datetime.strptime(
                self._get_last_backup_date(), FileOperation.DATE_FORMAT_OF_JSON_FILE
            )
            start_of_week, end_of_week = self._set_start_end_date(start_date, True)
        else:
            # getting start date as initial date from db
            start_date = self.db.get_start_date_from_db()
            start_of_week, end_of_week = self._set_start_end_date(start_date, False)
        return start_of_week, end_of_week

    def _set_start_end_date(self, start_date, backup):
        """
            Set startweek and endweek date.

            Parameters:
                start_date (Datetime object): start date of week
                backup (boolean): if lastbackupdate exist then True otherwise False 
            
            Returns:
                start_of_week (Datetime Object): start of the week from monday
                end_of_week (Datetime Object): end of the week to sunday
        """
        start_of_week = (
            start_date if backup else start_date - timedelta(days=start_date.weekday())
        )  # Monday
        end_of_week = start_of_week + timedelta(days=7)

        return start_of_week, end_of_week

    def create_file_name(self):
        """
            Creating filename for h5 file like
            25_February_2019_115407381000_to_04_March_2019_115407381000_20200118122012.h5.

            Parameters:
                None

            Returns:
                None 
        """
        start_timestamp = str(
            self.start_of_week.strftime(FileOperation.TIME_STAMP_WEEKLY_DATA)
        )
        end_timestamp = str(
            self.end_of_week.strftime(FileOperation.TIME_STAMP_WEEKLY_DATA)
        )
        current_timestamp = str(
            datetime.now().strftime(FileOperation.TIME_STAMP_FOR_DATA)
        )
        extension = ".h5"
        file_name = [
            start_timestamp,
            "to",
            end_timestamp,
            current_timestamp + extension,
        ]

        return "_".join(file_name)

    def _get_last_backup_date(self):
        """
            Fetching last back up date from json file.

            Parameters:
                None
                
            Returns:
                None 
        """
        with open(self.json_file_path, "r") as backup_file:
            backup_dict = json.load(backup_file)
        last_date = backup_dict["last_date"]
        return last_date

    def update_json(self, date_string):
        """
            Updating last back up date to json file.

            Parameters:
                date_string (String): last back up date as string 
                
            Returns:
                None 
        """
        with open(self.json_file_path, "w") as json_path:
            obj = {"last_date": date_string}
            json.dump(obj, json_path)

        self.s3.upload_file(
            self.json_file_path, FileOperation.JSON_FILE_NAME
        )  # uploading json file to s3 bucket.

    def to_hdf(self, data_frame):
        """
            Convert dataframe to hdf5 file format.

            Parameters:
                data_frame (DataFrame): Data Frame of weekly events data.
                
            Returns:
                None 
        """
        if data_frame is not None:
            data_frame.to_hdf(self.file_path, key=self.file_name, mode="a")

    def delete_local_h5(self):
        """
            Delete local h5 file.

            Parameters:
                None
                
            Returns:
                None 
        """
        for root, dirs, files in os.walk(FileOperation.BASE_PATH):
            for file in files:
                os.remove(os.path.join(root, file))

    def in_mins(self, start_time):
        """
            Convert seconds into minutes

            Parameters:
                start_time (Time): function start time
                
            Returns:
                mins (Time): start_time  in minutes
        """
        # returning in minutes
        mins = (time.time() - start_time) // 60
        return mins

    def current_day(self):
        """
            Get current day

            Parameters:
                None
                
            Returns:
                today (Datetime): current day
        """
        today = datetime.now()
        return today

    def fetch_data_from_cursor(self, start_time, data_cursor):
        """
            Fetch data from pymongo cursor object

            Parameters:
                start_time (Time): start time of function.
                data_cursor (Pymongo.cursor Object): contains references of
                data
                
            Returns:
                data_frame (Dataframe): contains cursor data in pandas
                dataframe.
        """
        data_list = []
        data_frame = None
        THRESHOLD = 60  # in percentage

        for data_counter, data in enumerate(data_cursor):
            mem = psutil.virtual_memory()

            # logging every 100000th iteration
            if data_counter % 100000 == 0:
                print("loaded data %s %s" % (data["createdAt"], data_counter))
            if self.in_mins(start_time) <= 10 and mem.percent <= THRESHOLD:

                data_list.append(data)
            else:
                self.end_of_week = data["createdAt"]
                print("Half file end of week", self.end_of_week)
                break
        if data_list:
            data_frame = pd.DataFrame(data_list)
            print(
                f"funtion completed {data_frame.shape},{self.start_of_week},{self.end_of_week}"
            )
        if data_frame.empty:
            data_frame = []
        return data_frame

    def delete_events_data(self):
        THRESHOLD = 60  # in percentage
        mem = psutil.virtual_memory()
        print(mem)
        if mem.percent <= THRESHOLD and self.current_day() > self.end_of_week:
            data_cursor = self.db.delete_week_data(self.start_of_week, self.end_of_week)
        else:
            self.end_of_week = self.end_of_week
        print(data_cursor)

    def main(self):
        """
           Iterate till current weekday and dump events weekly on aws s3 and
           update json file to s3.

           Parameters:
               None

           Returns:
               None
       """

        while True:

            if self.current_day() > self.end_of_week:
                print(f"Dumping data from {self.start_of_week} to , {self.end_of_week}")

                data_cursor = self.db.get_week_data(
                    self.start_of_week, self.end_of_week
                )  # getting data from db

                start_time = time.time()
                data_frame = self.fetch_data_from_cursor(start_time, data_cursor)

                if not data_frame.empty:
                    self.file_name = self.create_file_name()
                    self.file_path = os.path.join(
                        FileOperation.BASE_PATH, self.file_name
                    )
                    self.to_hdf(data_frame)
                    self.s3.upload_file(self.file_path, self.file_name)
                    self.delete_local_h5()
                    end_of_week_timestamp = self.end_of_week.strftime(
                        FileOperation.DATE_FORMAT_OF_JSON_FILE
                    )
                    self.update_json(end_of_week_timestamp)
                    print("UPDATE JSON")
                    del data_frame  # deleting dataframe
                    self.delete_events_data()
                    print("Deleted")
                    self.start_of_week = self.end_of_week
                    self.end_of_week = self.start_of_week + timedelta(days=7)
                else:
                    print("DataFrame is Empty")
                    break
            else:
                print(
                    "Dump Completed For Selected Date",
                    self.start_of_week,
                    self.end_of_week,
                )
                break


def lambda_handler(event=None, context=None):
    """
        Main lambda handler.
    """
    pdb.set_trace()
    obj_fileoperation = FileOperation()
    obj_fileoperation.main()
