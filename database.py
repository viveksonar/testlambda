import os

import pymongo as pymongo
from bson.json_util import dumps
from dotenv import load_dotenv


class Database:
    def __init__(self):
        """
            Constructor for Database class, initializing and defining
            variables.
        """
        self.client = pymongo.MongoClient(os.getenv("DATABASE_URL"))
        self.db = self.client[os.getenv("DATABASE_NAME")]

    def get_start_date_from_db(self):
        """
            Fetch initial date from database.
        
        Returns:
            start_date (Datetime): Initial event date
        """
        start_date = self.db.events.find_one()["createdAt"]
        return start_date

    def get_week_data(self, start_of_week, end_of_week):
        """
            Fetch week data from database for given time interval.
        
        Arguments:
            start_of_week (Datetime): Start date of the week 
            end_of_week (Datetime): End date of the week
        
        Returns:
            week_data (Pymongo.cursor Object): Weekly data for given time
            interval
        """
        week_data = (
            self.db.events.find(
                {"createdAt": {"$gte": start_of_week, "$lt": end_of_week}}
            )
            .sort("createdAt", 1)
            .batch_size(20000)
        )

        return week_data

    def delete_week_data(self, start_of_week, end_of_week):
        """
            Delete week data from database for given time interval.
        
        Arguments:
            start_of_week (Datetime): Start date of the week 
            end_of_week (Datetime): End date of the week
        
        """
        delete_week_data = self.db.events.remove(
            {
                "createdAt": {"$gte": start_of_week, "$lt": end_of_week},
                "kind": {"$nin": ["ApplicationStatusChangedEvent"]},
            }
        )

        return delete_week_data
