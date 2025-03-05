from django.shortcuts import render, redirect
from .models import FridgeItem
from .forms import FridgeItemForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

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
            messages.success(request, 'Produkt został dodany do lodówki!')
            return redirect('fridge_list')
    else:
        form = FridgeItemForm()
    return render(request, 'fridge/add_item.html', {'form': form})

@login_required
def edit_fridge_item(request, item_id):
    item = FridgeItem.objects.get(id=item_id, user=request.user)

    if request.method == 'POST':
        form = FridgeItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect('fridge_list')
    else:
        form = FridgeItemForm(instance=item)

    return render(request, 'fridge/edit_item.html', {'form': form})


@login_required
def delete_fridge_item(request, item_id):
    item = FridgeItem.objects.get(id=item_id, user=request.user)
    if request.method == 'POST':
        item.delete()
        messages.success(request, f'Produkt "{item.name}" został usunięty.')
        return redirect('fridge_list')

    return render(request, 'fridge/confirm_delete_item.html', {'item': item})