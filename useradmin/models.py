from django.db import models
from decimal import Decimal

# Create your models here.


class DashboardAnalytics(models.Model):
    date = models.DateField(auto_now_add=True)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    orders_count = models.IntegerField(default=0)
    products_count = models.IntegerField(default=0)
    monthly_earning = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Dashboard Analytics"
        verbose_name_plural = "Dashboard Analytics"

    def __str__(self):
        return f"Analytics for {self.date}"
