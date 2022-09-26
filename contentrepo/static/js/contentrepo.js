$(".meter > span").each(function () {
  $(this)
    .data("origWidth", $(this).width())
    .width(0)
    .animate(
      {
        width: $(this).data("origWidth")
      },
      1200
    );
});

function getUploadState(){
 $.ajax({
  url: '/import/',
  type: 'get',
  success: function(response){
   if(response != "True"){
    window.location.href = '/admin/home/contentpage/';
   }
  }
 });
}

$(document).ready(function(){
 var loadingBar = document.getElementById("loadingBar");
 if (loadingBar != null){
    setInterval(getUploadState,1000);
 }
});