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
            sendCartAction(productId, action, url)
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

function sendCartAction(productId, action, url) {
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
        console.log('data:', data)
        console.log(data.isLastItemInCart)

        if (data.isLastItemInCart) {
            location.replace('/')
        } else {
            location.reload()
        }
        })
}


$(function () {
  $('[data-toggle="tooltip"]').tooltip()
})