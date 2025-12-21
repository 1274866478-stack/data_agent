# AI Assistant Spec Delta

## MODIFIED Requirements

### File Data Source Handling

#### Requirement: Dynamic Excel File Discovery

**Modified from**: File path resolution relies on user-provided paths or system configuration.

**New behavior**: The system MUST implement dynamic file discovery for Excel files when the provided path cannot be resolved.

**Details**:
- When `inspect_file` or `analyze_dataframe` tools cannot find a file at the provided path, the system MUST automatically search for Excel files in `/app/uploads/` directory (recursively)
- If multiple Excel files are found, the system MUST select the most recently modified file
- If NO Excel files are found, the system MUST raise a `FileNotFoundError` with a clear error message (preventing AI hallucination)
- The system MUST log the discovered file path for debugging purposes

**Priority**: High (Critical for preventing AI hallucination)

**Scenario: User uploads Excel file with UUID filename**
```
Given: User uploads an Excel file named "users.xlsx"
And: System renames it to "5fe906a1-2b3c-4d5e-6f7a-8b9c0d1e2f3.xlsx"
And: File is stored at "/app/uploads/data-sources/tenant123/5fe906a1-2b3c-4d5e-6f7a-8b9c0d1e2f3.xlsx"
When: AI agent tries to read the file using user-provided path "users.xlsx"
Then: System should automatically discover the file at the UUID path
And: System should successfully read the file
And: AI should use actual data from the file (not hallucinate)
```

**Scenario: No Excel files uploaded**
```
Given: No Excel files exist in "/app/uploads/" directory
When: AI agent tries to read an Excel file
Then: System should raise FileNotFoundError with message "System Error: No Excel files found in /app/uploads/. Please confirm upload."
And: AI should NOT generate fake data
And: AI should return error message to user
```

**Scenario: Multiple Excel files exist**
```
Given: Multiple Excel files exist in "/app/uploads/" directory:
  - "/app/uploads/data-sources/tenant123/file1.xlsx" (modified 2024-01-01)
  - "/app/uploads/data-sources/tenant123/file2.xlsx" (modified 2024-01-02)
When: AI agent tries to read an Excel file without specifying path
Then: System should select file2.xlsx (most recently modified)
And: System should successfully read the selected file
```

**Scenario: User provides correct file path**
```
Given: User provides correct file path "file://data-sources/tenant123/5fe906a1-2b3c-4d5e-6f7a-8b9c0d1e2f3.xlsx"
When: AI agent tries to read the file
Then: System should use the provided path (not trigger dynamic discovery)
And: System should successfully read the file
```

### Error Handling for File Access

#### Requirement: Strict Error Messages for Missing Files

**Modified from**: Generic error messages when files cannot be found.

**New behavior**: The system MUST return explicit `SYSTEM ERROR` messages when files cannot be accessed, preventing AI from hallucinating data.

**Details**:
- When file discovery fails, return: `'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'`
- When no Excel files are found, raise `FileNotFoundError` with message: `"System Error: No Excel files found in /app/uploads/. Please confirm upload."`
- These error messages MUST be in the format that triggers the AI's "first line of defense" mechanism

**Priority**: High (Critical for preventing AI hallucination)

**Scenario: File not found triggers strict error**
```
Given: File path cannot be resolved and no Excel files exist in upload directory
When: AI agent calls inspect_file or analyze_dataframe
Then: System should return SYSTEM ERROR message
And: AI should NOT generate fake data
And: AI should return error message to user
```

