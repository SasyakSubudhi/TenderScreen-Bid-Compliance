from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
class Bid(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 tender_id: Literal['IITPKD-370']='IITPKD-370'
 bidder_name: str=Field(min_length=2,max_length=150)
 category: Literal['large','mse','startup','consortium','foreign','unknown']
 turnover_inr: list[int]=Field(min_length=5,max_length=5,description='FY2019-20 through FY2023-24 in INR')
 eligible_orders: int=Field(ge=0,le=10000)
 emd_paid_inr: int=Field(ge=0,le=10000000)
 exemption_claimed: bool=False
 recognition_id: str=Field(default='',max_length=100)
 own_goods_or_services: bool=True
 local_content_percent: int=Field(ge=0,le=100)
 documents: list[Literal['registration','pan','gst','audited_accounts','order_certificates','signed_tender','undertaking','non_debarment','local_content','authorization','fall_clause']]
 technical_compliance: Literal['declared','unknown']='declared'
 notes: str=Field(default='',max_length=2000)
 @model_validator(mode='after')
 def cross(self):
  if any(x<0 or x>10**12 for x in self.turnover_inr): raise ValueError('turnover values must be 0..10^12 INR')
  if self.exemption_claimed and (self.category not in ('mse','startup') or not self.recognition_id): raise ValueError('exemption requires MSE/startup category and recognition_id')
  if len(set(self.documents))!=len(self.documents): raise ValueError('duplicate documents')
  return self
class Feedback(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 satisfactory: bool
 reason: str=Field(min_length=3,max_length=1000)
class Decision(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 route: Literal['pass-to-technical-evaluation','seek-clarification','reject-with-cited-condition']
 human_review: bool
 basis: str
 findings: list[dict]
 citations: list[dict]
 prompt_version: str
 authority: Literal['screening recommendation only']='screening recommendation only'
