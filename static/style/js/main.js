/*  ---------------------------------------------------
    Template Name: Ogani
    Description:  Ogani eCommerce  HTML Template
    Author: Colorlib
    Author URI: https://colorlib.com
    Version: 1.0
    Created: Colorlib
---------------------------------------------------------  */

'use strict';

(function ($) {

    /*------------------
        Preloader
    --------------------*/
    $(window).on('load', function () {
        $(".loader").fadeOut();
        $("#preloder").delay(200).fadeOut("slow");

        /*------------------
            Gallery filter
        --------------------*/
        $('.featured__controls li').on('click', function () {
            $('.featured__controls li').removeClass('active');
            $(this).addClass('active');
        });
        if ($('.featured__filter').length > 0) {
            var containerEl = document.querySelector('.featured__filter');
            var mixer = mixitup(containerEl);
        }
    });

    /*------------------
        Background Set
    --------------------*/
    $('.set-bg').each(function () {
        var bg = $(this).data('setbg');
        $(this).css('background-image', 'url(' + bg + ')');
    });

    //Humberger Menu
    $(".humberger__open").on('click', function () {
        $(".humberger__menu__wrapper").addClass("show__humberger__menu__wrapper");
        $(".humberger__menu__overlay").addClass("active");
        $("body").addClass("over_hid");
    });

    $(".humberger__menu__overlay").on('click', function () {
        $(".humberger__menu__wrapper").removeClass("show__humberger__menu__wrapper");
        $(".humberger__menu__overlay").removeClass("active");
        $("body").removeClass("over_hid");
    });

    /*------------------
		Navigation
	--------------------*/
    $(".mobile-menu").slicknav({
        prependTo: '#mobile-menu-wrap',
        allowParentLinks: true
    });

    /*-----------------------
        Categories Slider
    ------------------------*/
    $(".categories__slider").owlCarousel({
        loop: true,
        margin: 0,
        items: 4,
        dots: false,
        nav: true,
        navText: ["<span class='fa fa-angle-left'><span/>", "<span class='fa fa-angle-right'><span/>"],
        animateOut: 'fadeOut',
        animateIn: 'fadeIn',
        smartSpeed: 1200,
        autoHeight: false,
        autoplay: true,
        responsive: {

            0: {
                items: 1,
            },

            480: {
                items: 2,
            },

            768: {
                items: 3,
            },

            992: {
                items: 4,
            }
        }
    });


    $('.hero__categories__all').on('click', function(){
        $('.hero__categories ul').slideToggle(400);
    });

    /*--------------------------
        Latest Product Slider
    ----------------------------*/
    $(".latest-product__slider").owlCarousel({
        loop: true,
        margin: 0,
        items: 1,
        dots: false,
        nav: true,
        navText: ["<span class='fa fa-angle-left'><span/>", "<span class='fa fa-angle-right'><span/>"],
        smartSpeed: 1200,
        autoHeight: false,
        autoplay: true
    });

    /*-----------------------------
        Product Discount Slider
    -------------------------------*/
    $(".product__discount__slider").owlCarousel({
        loop: true,
        margin: 0,
        items: 3,
        dots: true,
        smartSpeed: 1200,
        autoHeight: false,
        autoplay: true,
        responsive: {

            320: {
                items: 1,
            },

            480: {
                items: 2,
            },

            768: {
                items: 2,
            },

            992: {
                items: 3,
            }
        }
    });

    /*---------------------------------
        Product Details Pic Slider
    ----------------------------------*/
    $(".product__details__pic__slider").owlCarousel({
        loop: true,
        margin: 20,
        items: 4,
        dots: true,
        smartSpeed: 1200,
        autoHeight: false,
        autoplay: true
    });

    /*-----------------------
		Price Range Slider
	------------------------ */
    var rangeSlider = $(".price-range"),
        minamount = $("#minamount"),
        maxamount = $("#maxamount"),
        minPrice = rangeSlider.data('min'),
        maxPrice = rangeSlider.data('max');
    rangeSlider.slider({
        range: true,
        min: minPrice,
        max: maxPrice,
        values: [minPrice, maxPrice],
        slide: function (event, ui) {
            minamount.val('$' + ui.values[0]);
            maxamount.val('$' + ui.values[1]);
        }
    });
    minamount.val('$' + rangeSlider.slider("values", 0));
    maxamount.val('$' + rangeSlider.slider("values", 1));

    /*--------------------------
        Select
    ----------------------------*/
    $("select").niceSelect();

    /*------------------
		Single Product
	--------------------*/
    $('.product__details__pic__slider img').on('click', function () {

        var imgurl = $(this).data('imgbigurl');
        var bigImg = $('.product__details__pic__item--large').attr('src');
        if (imgurl != bigImg) {
            $('.product__details__pic__item--large').attr({
                src: imgurl
            });
        }
    });

    /*-------------------
		Quantity change
	--------------------- */
    var proQty = $('.pro-qty');
    proQty.prepend('<span class="dec qtybtn">-</span>');
    proQty.append('<span class="inc qtybtn">+</span>');
    proQty.on('click', '.qtybtn', function () {
        var $button = $(this);
        var oldValue = $button.parent().find('input').val();
        if ($button.hasClass('inc')) {
            var newVal = parseFloat(oldValue) + 1;
        } else {
            // Don't allow decrementing below zero
            if (oldValue > 0) {
                var newVal = parseFloat(oldValue) - 1;
            } else {
                newVal = 0;
            }
        }
        $button.parent().find('input').val(newVal);
    });

})(jQuery);











// // هذا هو ملف static/js/main.js

// // --- دالة لإظهار إشعار التوست (Toast) ---
// const cartToast = document.getElementById('cart-toast');
// const toastMessage = document.getElementById('toast-message');

// function showToast(message, isSuccess = true) {
//     if (!cartToast || !toastMessage) {
//         console.error("عنصر التوست أو رسالته غير موجودين في HTML. تأكد من وجود <div id=\"cart-toast\">.");
//         return; // توقف إذا كانت العناصر غير موجودة
//     }

//     toastMessage.textContent = message;
//     cartToast.classList.remove('error');
//     cartToast.querySelector('i').classList.remove('fa-exclamation-circle');
//     cartToast.querySelector('i').classList.add('fa-check-circle');

//     if (!isSuccess) {
//         cartToast.classList.add('error');
//         cartToast.querySelector('i').classList.add('fa-exclamation-circle');
//         cartToast.querySelector('i').classList.remove('fa-check-circle');
//     }

//     cartToast.classList.add('show');

//     setTimeout(() => {
//         cartToast.classList.remove('show');
//     }, 3000); // إخفاء التوست بعد 3 ثوانٍ
// }

// // --- جافا سكريبت لإضافات سلة التسوق باستخدام AJAX ---
// // نستمع لحدث إرسال كل نموذج يحمل الكلاس 'add-to-cart-form'
// document.querySelectorAll('.add-to-cart-form').forEach(form => {
//     form.addEventListener('submit', async function (event) {
//         event.preventDefault(); // منع الإرسال الافتراضي للنموذج (الذي يسبب إعادة التوجيه)

//         const formData = new FormData(this); // الحصول على بيانات النموذج (مثل quantity)
//         const actionUrl = this.action; // الحصول على عنوان URL الذي سيُرسل إليه الطلب (مثال: /cart/add_to_cart/3)

//         try {
//             const response = await fetch(actionUrl, {
//                 method: 'POST', // التأكد من إرسال الطلب كـ POST
//                 body: formData,
//                 headers: {
//                     'X-Requested-With': 'XMLHttpRequest' // هذا يُخبر الخادم بأن الطلب هو AJAX
//                 }
//             });

//             // التحقق مما إذا كانت الاستجابة JSON
//             const contentType = response.headers.get("content-type");
//             if (contentType && contentType.indexOf("application/json") !== -1) {
//                 const data = await response.json(); // تحليل استجابة JSON من الخادم

//                 if (data.success) {
//                     showToast(data.message, true); // إظهار رسالة نجاح باستخدام دالة التوست
//                 } else {
//                     showToast(data.message, false); // إظهار رسالة خطأ
//                 }
//             } else {
//                 console.error("لم يتم استلام استجابة JSON. قد تكون هناك مشكلة في الخادم أو إعادة توجيه غير متوقعة.");
//                 showToast('حدث خطأ غير متوقع في الخادم.', false);
//             }

//         } catch (error) {
//             console.error('خطأ أثناء الإضافة إلى سلة التسوق:', error);
//             showToast('حدث خطأ أثناء إضافة المنتج إلى سلة التسوق.', false);
//         }
//     });
// });

// // --- كود الإعجاب (Like) ---
// // (هذا الكود كان موجودًا لديك بالفعل)
// document.querySelectorAll('.like-btn').forEach(btn => {
//     btn.addEventListener('click', async function () {
//         const productId = this.dataset.productId;

//         try {
//             const response = await fetch(`/toggle_like/${productId}`, {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json',
//                 },
//                 credentials: 'include'
//             });

//             const data = await response.json();

//             if (!data.success && !data.is_authenticated) {
//                 Swal.fire({
//                     title: 'تحذير',
//                     text: data.message,
//                     icon: 'warning',
//                     showCancelButton: true,
//                     confirmButtonText: 'تسجيل الدخول',
//                     cancelButtonText: 'إلغاء'
//                 }).then((result) => {
//                     if (result.isConfirmed) {
//                         window.location.href = '/login';
//                     }
//                 });
//                 return;
//             }

//             if (data.success) {
//                 this.classList.toggle('liked');
//             }
//         } catch (error) {
//             console.error('Error:', error);
//         }
//     });
// });