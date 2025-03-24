// استرجاع السلة من الكوكيز
function getCart() {
    let cart = localStorage.getItem("cart");
    return cart ? JSON.parse(cart) : [];
}

// حفظ السلة في الكوكيز
function saveCart(cart) {
    localStorage.setItem("cart", JSON.stringify(cart));
}

// إضافة منتج إلى السلة
function addToCart(productId, name, price, image) {
    let cart = getCart();
    let existingItem = cart.find(item => item.id === productId);

    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        cart.push({ id: productId, name, price, image, quantity: 1 });
    }

    saveCart(cart);
    alert("تمت إضافة المنتج للسلة!");
}

// تحميل السلة عند فتح الصفحة
document.addEventListener("DOMContentLoaded", function () {
    let cart = getCart();
    let cartContainer = document.getElementById("cart-items");
    let totalAmount = 0;

    if (cart.length === 0) {
        cartContainer.innerHTML = "<p>السلة فارغة</p>";
    } else {
        cartContainer.innerHTML = cart.map(item => `
            <div>
                <img src="/static/uploads/${item.image}" width="50">
                <span>${item.name} - ${item.quantity} × ${item.price} ر.ي</span>
                <button onclick="removeFromCart(${item.id})">🗑</button>
            </div>
        `).join("");

        totalAmount = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        document.getElementById("total").innerText = `الإجمالي: ${totalAmount} ر.ي`;
    }
});

// حذف منتج من السلة
function removeFromCart(productId) {
    let cart = getCart().filter(item => item.id !== productId);
    saveCart(cart);
    location.reload();
}

// إتمام الطلب
function checkout() {
    fetch("/checkout", {
        method: "POST",
        body: new FormData(document.getElementById("checkout-form")),
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
        location.reload();
    });
}
