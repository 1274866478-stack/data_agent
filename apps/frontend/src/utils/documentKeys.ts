export const getDocumentUploadKey = (file: File): string =>
  `${file.name}_${file.size}_${file.lastModified}`
