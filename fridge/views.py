from django.shortcuts import render, redirect
from .models import FridgeItem
from .forms import FridgeItemForm
from django.contrib.auth.decorators import login_required

@login_required
def fridge_list(request):
    items = FridgeItem.objects.filter(user=request.user)
    return render(request, 'fridge/fridge_list.html', {'items': items})

@login_required
def add_fridge_item(request):
    if request.method == 'POST':
        form = FridgeItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            return redirect('fridge_list')
    else:
        form = FridgeItemForm()
    return render(request, 'fridge/add_item.html', {'form': form})
