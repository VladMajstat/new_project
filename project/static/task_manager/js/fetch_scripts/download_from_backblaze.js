document.addEventListener('DOMContentLoaded', function() {
  // Теперь элемент точно существует, и мы можем добавить обработчик
  const downloadButton = document.getElementById('downloadBackBlaze');
  
  if (downloadButton) {
    downloadButton.addEventListener('click', function(event) {
      event.preventDefault();
      const fileUrl = this.href;

      fetch(fileUrl)
        .then(response => response.blob())
        .then(blob => {
          const link = document.createElement('a');
          link.href = URL.createObjectURL(blob);
          
          let fileName = downloadButton.textContent;
          fileName = decodeURIComponent(fileName);

          link.download = fileName;
          link.click();
        })
        .catch(error => console.error('Ошибка при скачивании файла:', error));
    });
  } else {
    console.error('Элемент с id="downloadBackBlaze" не найден!');
  }
});  