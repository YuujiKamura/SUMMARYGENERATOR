# Survey Point（測点）補完のためのユーティリティクラス
class SurveyPoint
  # 許容する撮影時刻差（秒）- 5分
  DEFAULT_TIME_WINDOW = 300
  
  # 不完全な場所情報かどうかを判定
  # @param location [String, nil] 測点情報
  # @return [Boolean] 不完全な場合はtrue
  def self.incomplete_location?(location)
    return true if location.nil? || location.empty?
    
    location = location.strip
    
    # 'No.' が含まれるが数字が無い場合
    if location.include?('No.') && !location.match?(/\d/)
      return true
    end
    
    # 地名のみで No. が含まれていない場合（例：「小山」のみ）
    place_names = %w[小山 東区 西区 南区 北区]
    if !location.include?('No.') && place_names.any? { |name| location.include?(name) }
      return true
    end
    
    false
  end
  
  # 完全な測点情報を持つレコードから時刻-場所のルックアップテーブルを構築
  # @param records [Array<ResultRecord>] 全レコード
  # @return [Array<Array>] [[time, location], ...] の配列
  def self.build_time_lookup(records)
    lookup = []
    
    records.each do |record|
      next unless record.capture_time && record.location_value
      
      # 完全な場所情報のみを補完元として使用
      unless incomplete_location?(record.location_value)
        lookup << [record.capture_time, record.location_value]
      end
    end
    
    # 時刻順でソート
    lookup.sort_by { |time, _| time }
  end
  
  # 撮影時刻が近いレコードから場所を推定
  # @param target_time [Time] 対象の撮影時刻
  # @param time_lookup [Array] build_time_lookupで構築したルックアップテーブル
  # @param time_window [Integer] 許容する時刻差（秒）
  # @return [String, nil] 推定された場所、見つからない場合はnil
  def self.infer_location(target_time, time_lookup, time_window = DEFAULT_TIME_WINDOW)
    return nil unless target_time && !time_lookup.empty?
    
    # 最も近い時刻のレコードを見つける
    closest = time_lookup.min_by do |time, _|
      (target_time - time).abs
    end
    
    return nil unless closest
    
    closest_time, closest_location = closest
    time_diff = (target_time - closest_time).abs
    
    # 時刻差が許容範囲内であれば推定結果として返す
    time_diff <= time_window ? closest_location : nil
  end
  
  # 全レコードに対して場所情報の推定・補完を実行
  # @param records [Array<ResultRecord>] 全レコード
  # @param time_window [Integer] 許容する時刻差（秒）
  # @return [Array<ResultRecord>] 補完処理済みのレコード
  def self.supplement_all_locations(records, time_window = DEFAULT_TIME_WINDOW)
    return records if records.empty?
    
    # 完全な測点情報からルックアップテーブルを構築
    time_lookup = build_time_lookup(records)
    puts "補完元となる完全な測点情報: #{time_lookup.size}件"
    
    supplemented_count = 0
    
    records.each do |record|
      # 不完全な場所情報を持つレコードに対して推定を実行
      if record.needs?('location') && record.capture_time
        inferred = infer_location(record.capture_time, time_lookup, time_window)
        if inferred
          record.inferred_location = inferred
          supplemented_count += 1
          puts "場所推定: #{File.basename(record.image_path)} -> #{inferred}"
        end
      end
    end
    
    puts "場所情報補完数: #{supplemented_count}件"
    records
  end
  
  # 統計情報を出力
  # @param records [Array<ResultRecord>] 全レコード
  def self.print_statistics(records)
    total = records.size
    located_count = records.count(&:located?)
    has_location_count = records.count(&:has_location?)
    inferred_count = records.count { |r| r.inferred_location }
    date_count_count = records.count(&:has_date_count?)
    
    puts "\n=== Survey Point 統計情報 ==="
    puts "総処理ファイル数: #{total}"
    puts "測点名称検出数 (OCR成功): #{located_count}"
    puts "測点名称補完数: #{inferred_count}"
    puts "未取得: #{total - has_location_count - inferred_count}"
    puts "日付・台数検出数: #{date_count_count}"
  end
end
