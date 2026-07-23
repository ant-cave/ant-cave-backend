# API 参考

## 健康检查

### `GET /api/health`

服务健康检查。

```json
{"status": "ok"}
```

## 系统统计

### `GET /api/stats`

返回系统统计数据：各目录图片数量、向量数据库信息、当前任务列表。

## WebSocket

### `WS /api/ws/{task_id}`

订阅指定任务的实时运行进度。消息格式：

```json
{"event": "progress|log|complete|error", "stage": "...", "current": 0, "total": 100, "message": "..."}
```

---

## 管线

前缀 `/api/pipeline`

### `POST /api/pipeline/auto`

提交自动分类管线任务。请求体接受 `AutoParams`：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_folder` | string | `input/auto_uploads` | 输入图片目录 |
| `buffer` | string | `buffer/auto` | 缓冲区目录 |
| `db_name` | string | `features.fvdb` | 特征库文件名 |
| `output_folder` | string | `output/auto/classify` | 输出目录 |
| `conf` | float | `0.5` | YOLO 置信度阈值 |
| `iou` | float | `0.45` | IoU 阈值 |
| `imgsz` | int | `1280` | 检测输入尺寸 |
| `eps_start` | float | `1.0` | DBSCAN eps 起始值 |
| `eps_stop` | float | `2.0` | DBSCAN eps 结束值 |
| `eps_step` | float | `0.01` | DBSCAN eps 步长 |
| `use_augmentation` | bool | `true` | 是否启用数据增强 |
| `augmentation_count` | int | `4` | 每张图片增强数量 |
| `existing_run_id` | string | `""` | 追加模式的已有 run_id |

返回：

```json
{"task_id": "abc123def456"}
```

### `GET /api/pipeline/tasks`

列出所有任务（排队中、运行中、已完成、失败）。

### `GET /api/pipeline/tasks/{task_id}`

获取单个任务详情。

---

## 结果

前缀 `/api/results`

### `GET /api/results/auto`

列出所有完成的自动分类运行。

```json
{"runs": [...], "count": 3}
```

### `GET /api/results/auto/run/{run_id}`

获取单个运行的元数据。

### `DELETE /api/results/auto/run/{run_id}`

删除指定运行（输出目录、缓冲区目录、数据库记录一并清除）。

### `GET /api/results/auto/run/{run_id}/image/{path}`

获取运行结果中的某张图片。支持 `?thumb=1` 缩略图模式。

### `GET /api/results/auto/run/{run_id}/zip`

下载运行的聚类结果 ZIP 包（仅包含图片）。

---

## 图片管理

前缀 `/api/images`

### `GET /api/images/{category}`

列出分类目录中的图片文件。

分类：`images`、`sim_targets`、`id_targets`、`auto_uploads`

### `GET /api/images/{category}/image/{filename}`

获取图片文件。支持 `?thumb=1` 缩略图。

### `POST /api/images/{category}/upload`

上传图片（multipart/form-data）。限制：最多 100 个文件、单文件最大 50MB、总量最大 500MB、仅支持 JPG/PNG/WebP。

### `DELETE /api/images/{category}/{filename}`

删除图片文件。
