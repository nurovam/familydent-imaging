window.config = {
  routerBasename: '/',
  showStudyList: false,
  extensions: [], modes: [],
  showWarningMessageForCrossOrigin: false,
  showCPUFallbackMessage: true,
  investigationalUseDialog: { option: 'always' },
  dataSources: [{
    namespace: '@ohif/extension-default.dataSourcesModule.dicomweb',
    sourceName: 'familydent',
    configuration: {
      friendlyName: 'FamilyDent — synthetic local preview', name: 'familydent',
      wadoUriRoot: '/api/imaging/dicom-web', qidoRoot: '/api/imaging/dicom-web', wadoRoot: '/api/imaging/dicom-web',
      qidoSupportsIncludeField: true, supportsFuzzyMatching: false, supportsWildcard: false,
      imageRendering: 'wadors', thumbnailRendering: 'wadors', enableStudyLazyLoad: true,
      dicomUploadEnabled: false, bulkDataURI: { enabled: false },
    },
  }],
  defaultDataSourceName: 'familydent',
};
