from django.db import models
import datetime
# Create your models here.
class history(models.Model):
    username = models.CharField(max_length=100)
    history = models.CharField(max_length=100)
    time = models.TimeField(default=datetime.datetime.now())

class state(models.Model):
    username = models.CharField(max_length=100)
    year = models.CharField(max_length=4)
    search_by = models.CharField(default="default",max_length=100)
    theme = models.CharField(max_length=5)
    
    