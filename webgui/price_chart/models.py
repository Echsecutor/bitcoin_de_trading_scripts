from django.db import models


class BitcoinDe(models.Model):
    trading_pair = models.CharField(max_length=6)
    date = models.DateTimeField()
    price = models.DecimalField(max_digits=12, decimal_places=3)
    amount = models.DecimalField(max_digits=16, decimal_places=10)
    tid = models.PositiveIntegerField(primary_key=True)


class ShapeshiftMarketinfo(models.Model):
    trading_pair = models.CharField(max_length=6)
    date = models.DateTimeField()
    rate = models.DecimalField(max_digits=16, decimal_places=10)
    minerfee = models.DecimalField(max_digits=16, decimal_places=10)


class ShapeshiftTransactions(models.Model):
    trading_pair = models.CharField(max_length=6)
    date = models.DateTimeField()
    amount = models.DecimalField(max_digits=16, decimal_places=10)

