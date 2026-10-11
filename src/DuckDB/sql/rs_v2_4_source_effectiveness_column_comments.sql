-- CherryStock R/S V2.4: Vietnamese column comments for the public source-effectiveness view.
-- Metadata-only, idempotent. Run after rs_v2_4_source_effectiveness.sql creates the view.
-- IMPORTANT: CREATE OR REPLACE VIEW may reset comments; reapply this script after view recreation.
-- No data mutation or runtime-scoring changes.
COMMENT ON VIEW "CherryMon"."main"."vw_RS_Source_Effectiveness" IS 'R/S V2.4: ket qua source effectiveness moi nhat theo ticker, scope, source va horizon; chi phuc vu nghien cuu/governance, khong tu dong thay doi runtime.';

COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."Ticker" IS 'Mã cổ phiếu được đánh giá hiệu quả nguồn R/S.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."ScopeType" IS 'Phạm vi ablation: SOURCE_CONFIG (một source/config) hoặc SOURCE_FAMILY (cả nhóm source).';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."SourceKey" IS 'Định danh canonical của source/config hoặc family được đánh giá; đọc cùng ScopeType.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."SourceFamily" IS 'Nhóm ngữ nghĩa của nguồn R/S, ví dụ TREND_AVERAGE, MARKET_STRUCTURE, VOLUME_STRUCTURE.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."SourceRole" IS 'Vai trò nguồn: LEVEL tạo vùng giá; CONTEXT cung cấp bối cảnh; CONFIRMATION xác nhận Strength.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."HorizonBars" IS 'Số thanh giá trong tương lai dùng để đánh giá kết quả R/S; không phải timeframe của indicator.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."AttributionMode" IS 'Cách quy công: LEVEL_LINEAGE, MARGINAL_ONLY hoặc FAMILY_ABLATION.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."MarginalMetric" IS 'Thước đo dùng tính lift khi bỏ nguồn: LEVEL_QUALITY hoặc STRENGTH_BRIER (chất lượng 1 - Brier loss).';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."LineageEventCount" IS 'Số historical events thuộc lineage của source; chủ yếu có ý nghĩa với SourceRole=LEVEL.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."ValidationEventCount" IS 'Số event của baseline trong tập VALIDATION cho ticker/horizon đang xét.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."TestEventCount" IS 'Số event của baseline trong tập TEST ngoài mẫu cho ticker/horizon đang xét.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."TouchRate" IS 'Tỷ lệ vùng R/S có giá chạm trong horizon; giá trị dạng tỷ lệ 0..1, có thể NULL khi không áp dụng.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."HoldRateGivenTouch" IS 'Tỷ lệ giữ vùng trong số event đã chạm; mẫu số là số event Touched, không phải tổng event.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."BreakRateGivenTouch" IS 'Tỷ lệ phá vùng trong số event đã chạm; mẫu số là số event Touched.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."RetestRateGivenBreak" IS 'Tỷ lệ retest trong số event đã phá vùng; mẫu số là số event Broken theo evaluation contract.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."DirectionalEdgePct" IS 'Mức dịch chuyển thuận chiều sau phản ứng R/S, tính theo phần trăm giá; có thể âm.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."ValidationQuality" IS 'Điểm chất lượng baseline trên VALIDATION; thước đo phụ thuộc MarginalMetric.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."TestQuality" IS 'Điểm chất lượng baseline trên TEST; thước đo phụ thuộc MarginalMetric.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."ValidationMarginalLift" IS 'ValidationQuality của baseline có nguồn trừ quality của ablation bỏ nguồn; dương nghĩa nguồn hữu ích.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."TestMarginalLift" IS 'TestQuality của baseline có nguồn trừ quality của ablation bỏ nguồn trên TEST; dương là cải thiện ngoài mẫu.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."TemporalStability" IS 'Độ ổn định chất lượng giữa VALIDATION và TEST, chuẩn hóa 0..1; cao hơn là ổn định hơn.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."RegimeStability" IS 'Độ ổn định chất lượng/lift qua các market regime, chuẩn hóa 0..1; NULL nếu không đủ regime.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."ComplexityDelta" IS 'Chênh lệch độ phức tạp của model khi có nguồn so với ablation; dùng làm penalty.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."EffectivenessScore" IS 'Điểm tổng hợp hiệu quả lịch sử của nguồn (0..100), có xét chất lượng, lift, stability và penalty; không phải R/S StrengthScore.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."Recommendation" IS 'Phân loại theo ticker/source/horizon: CORE, SUPPORTING, CONFIRM_ONLY, CONTEXT_ONLY, RESEARCH hoặc DROP; không tự động promote production.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."EvidenceJson" IS 'JSON chứa số liệu thành phần, policy và giải trình phục vụ audit/diễn giải kết quả.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."EffectivenessRunId" IS 'ID của lượt đánh giá effectiveness được chọn làm bản mới nhất hoàn tất cho grain này.';
COMMENT ON COLUMN "CherryMon"."main"."vw_RS_Source_Effectiveness"."CompletedAt" IS 'Thời điểm hoàn tất lượt evaluation, dùng chọn bản mới nhất; không phải thời điểm dữ liệu giá.';

-- Verification: should return 28 rows, with non-null comments.
SELECT column_name, comment
FROM duckdb_columns()
WHERE database_name = 'CherryMon'
  AND schema_name = 'main'
  AND table_name = 'vw_RS_Source_Effectiveness'
ORDER BY column_index;
