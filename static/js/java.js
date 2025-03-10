$(function () {
  "use strict";

  $(".toggle-info").click(function () {
    $(this)
      .toggleClass("selected")
      .parent()
      .next(".panel-body")
      .fadeToggle(100);

    if ($(this).hasClass("selected")) {
      $(this).html('<i class="fa fa-minus fa-lg"></i>'); //عند النقر على زر ال+ يرجع _ا
    } else {
      $(this).html('<i class="fa fa-plus fa-lg"></i>'); //عند النقر على زر ال+ يرجع _ا
    }
  });

  // $("select").selectBoxIt();
  // $("[placeholder]")
  //   .focus(function () {
  //     $(this).attr("data-text", $(this).attr("placeholder"));
  //     $(this).attr("placeholder", ""); //لاخفاء اسم المستخدم عند وضع المؤشر عليه
  //   })
  //   .blur(function () {
  //     $(this).attr("placeholder".$(this).attr("data-text")); //عند سحب المؤشر من مربع النص تعود كلمه اسم المستخدم الى المربع
  //   });

  //    $('input').each(function(){//each تشيك على كل الحقول
  //      if($(this).attr('required')==='required'){
  //        $(this).after('<span class="asterisk">*</span>');
  //      }
  //    });
  var passfield = $(".password");
  $(".show-pass").hover(
    function () {
      passfield.attr("type", "text");
    },
    function () {
      passfield.attr("type", "password");
    }
  );

  // confirmation message on bottun
  $(".confirm").click(function () {
    return confirm("Are you Sure?");
  });

  //هذه الدالة عند النقر على كلمة تقوم ب اظهار النص الذي تحتها

  $(".cat h3").click(function () {
    $(this).next(".full-view").fadeToggle(200);
  });
  //58
  $(".option span").click(function () {
    $(this).addClass("active").siblings("span").removeClass("active"); //اشر على الاكلاسات التي تحتوي على كلاس اكتيف

    if ($(this).data("view") === "full") {
      $(".cat .full-view").fadeIn(200);
    } else {
      $(".cat .full-view").fadeOut(200);
    }
  });
  //show delelet 
  //وظيفه الداله الاولى اذا سويت هافر على القسم الفرعي اظهر لي الحذف او التعديل
 $('.child-link').hover(function(){

   $(this).find('.show-delete').fadeIn(400);
 },function(){
  //اذا ابتعد عن اسم القسم الفرعي يختفي زر الحذف و التعديل
  $(this).find('.show-delete').fadeOut(400);
 });

}); //end

//لايعمل هذة الكود
