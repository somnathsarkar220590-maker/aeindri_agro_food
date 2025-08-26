from django.contrib import admin
from django.urls import path, include

# এখানে অ্যাডমিন সাইটের টাইটেল পরিবর্তন করা হচ্ছে
admin.site.site_header = "AEINDRI AGRO FOOD PRODUCT PVT. LTD. Powered by NoCode Solution"
admin.site.site_title = "AEINDRI AGRO"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('management.urls')),
]