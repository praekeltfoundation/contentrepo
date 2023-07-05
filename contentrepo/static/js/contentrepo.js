getUploadStateInterval = null;

function getUploadState(){
 $.getJSON({
  url: importURL,
  success: function(response){
   if(!response.loading){
    window.location.href = destinationURL;
    clearInterval(getUploadStateInterval)
   }
   if(response.progress) {
      $(".meter > span").each(function () {
        $(this)
          .animate(
            {
              width: response.progress + "%"
            },
            1200
          );
      });
    }
  }
 });
}

$(document).ready(function(){
 var loadingBar = document.getElementById("loadingBar");
 if (loadingBar != null){
    getUploadStateInterval = setInterval(getUploadState,1000);
 }
});
