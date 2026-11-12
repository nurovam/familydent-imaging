window.config = {
  routerBasename: '/',
  showStudyList: false,
  extensions: [], modes: [],
  showWarningMessageForCrossOrigin: false,
  showCPUFallbackMessage: true,
  investigationalUseDialog: { option: 'always' },
  dataSources: [{
    namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
    sourceName: 'synthetic',
    configuration: {
      friendlyName: 'SYNTHETIC ONLY', name: 'synthetic',
      wadoUriRoot: '/dicom-web', qidoRoot: '/dicom-web', wadoRoot: '/dicom-web',
      qidoSupportsIncludeField: true, supportsFuzzyMatching: false, supportsWildcard: false,
      imageRendering: 'wadors', thumbnailRendering: 'wadors', enableStudyLazyLoad: true,
      dicomUploadEnabled: false, bulkDataURI: { enabled: false },
    },
  }],
  defaultDataSourceName: 'synthetic',
};
