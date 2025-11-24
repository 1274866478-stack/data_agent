import { renderHook, act } from '@testing-library/react';
import { useDataSourceStore } from '../dataSourceStore';

describe('dataSourceStore', () => {
  beforeEach(() => {
    // Reset store before each test
    const { result } = renderHook(() => useDataSourceStore());
    act(() => {
      result.current.clearDataSources();
    });
  });

  it('should initialize with empty data sources', () => {
    const { result } = renderHook(() => useDataSourceStore());
    
    expect(result.current.dataSources).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should set loading state', () => {
    const { result } = renderHook(() => useDataSourceStore());
    
    act(() => {
      result.current.setLoading(true);
    });

    expect(result.current.isLoading).toBe(true);
  });

  it('should set error state', () => {
    const { result } = renderHook(() => useDataSourceStore());
    
    const errorMessage = 'Failed to fetch data sources';

    act(() => {
      result.current.setError(errorMessage);
    });

    expect(result.current.error).toBe(errorMessage);
  });

  it('should add data source', () => {
    const { result } = renderHook(() => useDataSourceStore());
    
    const mockDataSource = {
      id: 'ds_123',
      name: 'Test Database',
      type: 'postgresql',
      status: 'active',
      createdAt: new Date().toISOString(),
    };

    act(() => {
      result.current.addDataSource(mockDataSource);
    });

    expect(result.current.dataSources).toHaveLength(1);
    expect(result.current.dataSources[0]).toEqual(mockDataSource);
  });

  it('should update data source', () => {
    const { result } = renderHook(() => useDataSourceStore());
    
    const mockDataSource = {
      id: 'ds_123',
      name: 'Test Database',
      type: 'postgresql',
      status: 'active',
      createdAt: new Date().toISOString(),
    };

    // Add data source first
    act(() => {
      result.current.addDataSource(mockDataSource);
    });

    // Update data source
    const updatedDataSource = {
      ...mockDataSource,
      name: 'Updated Database',
    };

    act(() => {
      result.current.updateDataSource('ds_123', updatedDataSource);
    });

    expect(result.current.dataSources[0].name).toBe('Updated Database');
  });

  it('should remove data source', () => {
    const { result } = renderHook(() => useDataSourceStore());
    
    const mockDataSource = {
      id: 'ds_123',
      name: 'Test Database',
      type: 'postgresql',
      status: 'active',
      createdAt: new Date().toISOString(),
    };

    // Add data source first
    act(() => {
      result.current.addDataSource(mockDataSource);
    });

    expect(result.current.dataSources).toHaveLength(1);

    // Remove data source
    act(() => {
      result.current.removeDataSource('ds_123');
    });

    expect(result.current.dataSources).toHaveLength(0);
  });

  it('should set multiple data sources', () => {
    const { result } = renderHook(() => useDataSourceStore());
    
    const mockDataSources = [
      {
        id: 'ds_1',
        name: 'Database 1',
        type: 'postgresql',
        status: 'active',
        createdAt: new Date().toISOString(),
      },
      {
        id: 'ds_2',
        name: 'Database 2',
        type: 'mysql',
        status: 'active',
        createdAt: new Date().toISOString(),
      },
    ];

    act(() => {
      result.current.setDataSources(mockDataSources);
    });

    expect(result.current.dataSources).toHaveLength(2);
    expect(result.current.dataSources).toEqual(mockDataSources);
  });
});

