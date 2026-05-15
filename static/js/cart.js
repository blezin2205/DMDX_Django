var updateBtns = document.getElementsByClassName('update-cart')
var updateDetailBtns = document.getElementsByClassName('update-cart-detail')
var updateOrderStatusBtns = document.getElementsByClassName('update-order-status')
var deleteBtns = document.getElementsByClassName('delete-supp-button')
// var deleteSuppInOrderBtns = document.getElementsByClassName('delete-suppinorder-button')
var deletenpdocumentbutton = document.getElementsByClassName('delete-npdocument-button')
// var update_count_in_order = document.getElementsByClassName('update-order-count')
var preorder_general_supp_buttons = document.getElementsByClassName('preorder-general-supp-button')

for(var a = 0; a < deleteBtns.length; a++) {
    deleteBtns[a].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action

        var url = 'delete_supply/'
        senadAction(productId, action, url)

    })
}

for(var a = 0; a < preorder_general_supp_buttons.length; a++) {
    preorder_general_supp_buttons[a].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action

        var url = '/preorder_general_supp_buttons/'
        senadAction(productId, action, url)

    })
}

// for(var a = 0; a < update_count_in_order.length; a++) {
//     update_count_in_order[a].addEventListener('click', function () {
//         var productId = this.dataset.product
//         var action = this.dataset.action
//
//         var url = '/update_order_count/'
//         senadAction(productId, action, url)
//
//     })
// }

// for(var a = 0; a < deleteSuppInOrderBtns.length; a++) {
//     deleteSuppInOrderBtns[a].addEventListener('click', function () {
//         var productId = this.dataset.product
//         var action = this.dataset.action
//         console.log('Prinet delete action')
//
//         var url = '/delete_supply_in_order/'
//         senadAction(productId, action, url)
//
//     })
// }

for(var a = 0; a < deletenpdocumentbutton.length; a++) {
    deletenpdocumentbutton[a].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action
        console.log('Prinet delete action')

        var url = '/deleteSupplyInOrderNPDocumentButton/'
        senadAction(productId, action, url)

    })
}

for(var a = 0; a < updateOrderStatusBtns.length; a++) {
    updateOrderStatusBtns[a].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action
        var url = '/orders_update_status/'
        senadAction(productId, action, url)
    })
}

for(var i = 0; i < updateBtns.length; i++) {
    updateBtns[i].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action
        console.log('id:', productId, 'action:', action)

        console.log('Print log')
         var url = '/update_item/'

        console.log('USER:', user)
        if (user === 'AnonymousUser') {
            console.log('Not logged in')
        } else {
            senadAction(productId, action, url)
        }
    })
}

for(var i = 0; i < updateDetailBtns.length; i++) {
    updateDetailBtns[i].addEventListener('click', function () {
        var productId = this.dataset.product
        var action = this.dataset.action
        console.log('id:', productId, 'action:', action)

        console.log('Print log')
         var url = 'update_item/'

        console.log('USER:', user)
        if (user === 'AnonymousUser') {
            console.log('Not logged in')
        } else {
            sendCartAction(productId, action, url, this)
        }
    })
}


function senadAction(productId, action, url) {
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({'productId': productId, 'action': action})
    })

     .then((response) =>{
            return response.json()
        })

    .then((data) => {
        location.reload()
        })
}

function getNextRedirectUrl() {
    const hiddenNextInput = document.querySelector('input[name="next"]');
    const queryNext = new URLSearchParams(window.location.search).get('next');
    const nextValue = (hiddenNextInput && hiddenNextInput.value) || queryNext || '/';
    const fallbackUrl = '/';

    if (!nextValue || nextValue === 'None') {
        return fallbackUrl;
    }

    try {
        const parsedUrl = new URL(nextValue, window.location.origin);
        const forbiddenPaths = new Set([
            '/update-cart-item-count/',
            '/update-precart-item-count/',
            '/cart/update_item/',
            '/preorders-cart/update_item/',
        ]);

        if (forbiddenPaths.has(parsedUrl.pathname)) {
            return fallbackUrl;
        }
    } catch (error) {
        return fallbackUrl;
    }

    return nextValue;
}

function updateCartBadge(action) {
    if (!window.htmx) {
        return;
    }

    const eventName = action === 'delete-precart' ? 'subscribe_precart' : 'subscribe';
    htmx.trigger(document.body, eventName, {});
}

function updateCartTotal(removedCount) {
    const totalElement = document.getElementById('cart-total-count');
    if (!totalElement || Number.isNaN(removedCount)) {
        return;
    }

    const totalMatch = totalElement.textContent.match(/\d+/);
    if (!totalMatch) {
        return;
    }

    const currentTotal = parseInt(totalMatch[0], 10);
    const nextTotal = Math.max(currentTotal - removedCount, 0);
    totalElement.textContent = `${nextTotal} шт.`;
}

function sendCartAction(productId, action, url, clickedButton) {
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({'productId': productId, 'action': action, 'next': getNextRedirectUrl()})
    })
    .then((response) => {
        return response.json()
    })
    .then((data) => {
        console.log('data:', data)
        console.log(data.isLastItemInCart)

        if (data.isLastItemInCart) {
            location.replace(data.redirectUrl || getNextRedirectUrl() || '/')
        } else {
            const itemRow = clickedButton && clickedButton.closest('[data-cart-item-row]');
            if (itemRow) {
                const removedCount = parseInt(itemRow.dataset.itemCount || '0', 10);
                itemRow.remove();
                updateCartTotal(removedCount);
            } else {
                location.reload();
                return;
            }

            updateCartBadge(action);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function updateOrderStatus(orderId) {
    fetch(`orders_update_status/${orderId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({'productId': orderId, 'action': 'update'})
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.text();
    })
    .then(html => {
        // Update just the order preview cell
        const orderCell = document.getElementById(`order_preview_cell${orderId}`);
        if (orderCell) {
            orderCell.innerHTML = html;
        }
    })
    .catch(error => {
        alert(error.message || 'Error updating order status');
        console.error('Error updating order status:', error);
    });
}

$(function () {
  $('[data-toggle="tooltip"]').tooltip()
})