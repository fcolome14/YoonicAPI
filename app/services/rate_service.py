from sqlalchemy.orm import Session
from typing import List, Union
from app.models import Rates
from app.schemas import RateDetails, NewPostInput
from app.models import EventsLines
from app.utils import utils

class RateService:
    @staticmethod
    def add_rates(fetched_data: NewPostInput, db: Session, rates_dict: dict, db_ids_dict: dict):
        if isinstance(fetched_data.line, List):
            return RateService.multiple_lines(db, rates_dict, db_ids_dict)
        return RateService.single_line(db, rates_dict, db_ids_dict)

    def multiple_lines(db: Session, rates_dict: dict[int, RateDetails], db_ids_dict: dict[int, int]):
        rates = []
        for key, line_ids in db_ids_dict.items():
            if key in rates_dict:
                rate_list = rates_dict[key]
                line_ids = line_ids if isinstance(line_ids, list) else [line_ids]

                for rate in rate_list:
                    for line_id in line_ids:
                        rates.append(Rates(
                            title=rate.title,
                            amount=rate.amount,
                            currency=rate.currency,
                            line_id=line_id
                        ))
                        
        db.add_all(rates)
        db.commit()
        
        for item in rates:
            db.refresh(item)
        
        rates_id = [rate.id for rate in rates]
        return {"status": "success", "details": f"Added {rates_id} rates"}

    
    def single_line(db: Session, rates_dict: dict[int, RateDetails | list[RateDetails]], db_ids_dict: dict[int, list[int]]):
        rates = []
        
        for id_list in db_ids_dict.values():
            for rate_list in rates_dict.values():
                rate_list = rate_list if isinstance(rate_list, list) else [rate_list]
                
                for rate in rate_list:
                    for db_id in id_list:
                        rates.append(Rates(
                            title=rate.title,
                            amount=rate.amount,
                            currency=rate.currency,
                            line_id=db_id
                        ))

        db.add_all(rates)
        db.commit()

        for item in rates:
            db.refresh(item)
        rates_id = [rate.id for rate in rates]

        return {"status": "success", "details": f"Added {rates_id} rates"}
    
    
def pack_rates(fetched_data: NewPostInput, lines_db: Union[List[EventsLines], EventsLines]):
    rates_dict = {}
    db_ids_dict = {}
    index = 0

    lines = [line.id for line in lines_db] if isinstance(lines_db, list) else [lines_db.id]

    def process_rates(day, index):
        rates = []
        if hasattr(day, 'rate'):
            if isinstance(day.rate, list):
                rates.extend(day.rate)
            else:
                rates.append(day.rate)
        rates_dict[index] = rates

    if fetched_data.repeat:
        if isinstance(fetched_data.line, list):
            for day in fetched_data.line:
                process_rates(day, index)
                index += 1
            db_ids_dict = utils.split_array_to_dict(lines, fetched_data.occurrences)
            return rates_dict, db_ids_dict

    if isinstance(fetched_data.line, list):
        for day in fetched_data.line:
            process_rates(day, index)
            index += 1
        db_ids_dict = utils.split_array_to_dict(lines, freq=1)
        return rates_dict, db_ids_dict

    if hasattr(fetched_data.line, 'rate'):
        if isinstance(fetched_data.line.rate, list):
            rates_dict[0] = fetched_data.line.rate
        else:
            rates_dict[0] = [fetched_data.line.rate]
    db_ids_dict[0] = lines

    return rates_dict, db_ids_dict
