export const readFile = (file: File): Promise<string | undefined> => {
  return new Promise<string | undefined>((resolve, reject) => {
    let fileReader = new FileReader();
    fileReader.onload = () => {
      const result = fileReader.result?.toString();
      resolve(result);
    };
    fileReader.onerror = reject;
    fileReader.readAsText(file);
  });
};

export const downloadFile = (data: string, filename: string) => {
  const link = document.createElement('a');

  link.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(data));
  link.setAttribute('download', filename || 'data.json');
  link.style.display = 'none';

  document.body.appendChild(link);

  link.click();

  document.body.removeChild(link);
};
