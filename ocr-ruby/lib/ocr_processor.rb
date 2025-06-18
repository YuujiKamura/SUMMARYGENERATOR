require_relative 'document_ai_client'
require_relative 'survey_point'
require_relative 'exif_reader'
require 'json'
require 'pathname'

# OCR処理のメインプロセッサークラス
class OCRProcessor
  attr_reader :document_ai, :results, :time_window
  
  def initialize(config_path: nil, time_window: 300)
    @document_ai = DocumentAIClient.new(config_path)
    @results = []
    @time_window = time_window  # Survey Point補完の時刻窓（秒）
    @processed = {}  # キャッシュ用
  end
  
  # 複数画像を一括処理
  # @param image_paths [Array<String>] 処理対象の画像パス一覧
  # @return [Array<ResultRecord>] 処理結果
  def process_images(image_paths)
    puts "=== OCR処理開始 ==="
    puts "対象画像数: #{image_paths.size}件"
    
    @results = []
    @image_entries = nil
    
    # 呼び出し側で並び替え済みとみなし、受け取った順で処理
    # （必要なら capture_time ソートのメソッドも残している）
    sorted_images = image_paths
    
    # 各画像を処理
    sorted_images.each_with_index do |image_path, index|
      puts "\n--- 画像 #{index + 1}/#{sorted_images.size} ---"
      puts "ファイル: #{File.basename(image_path)}"
      
      result = process_single_image(image_path)
      @results << result
      
      # リアルタイム補完処理
      perform_realtime_supplement(result, index)
    end
    
    # 後処理: 不完全な場所を前後画像で補完
    SurveyPoint.supplement_all_locations(@results, @time_window)
    # 追加: 前後エントリから location/date_count の補完
    SurveyPoint.supplement_from_neighbors_all(@results, @time_window)
    
    # 最終的な統計情報表示
    SurveyPoint.print_statistics(@results)
    
    @results
  end
  
  # 単一画像を処理
  # @param image_path [String] 画像ファイルのパス
  # @return [ResultRecord] 処理結果
  def process_single_image(image_path)
    # EXIF情報から撮影時刻を取得
    capture_time = ExifReader.capture_time_with_fallback(image_path)
    
    # DocumentAI でOCR実行
    ocr_result = @document_ai.extract_text(image_path)
    
    # 撮影時刻を上書き
    ocr_result['capture_time'] = capture_time
    
    # ResultRecord に変換
    record = SurveyPoint.from_raw(ocr_result)
    
    # 結果表示
    display_result(record)
    
    record
  end
  
  # リアルタイム補完処理（各画像処理後に実行）
  def perform_realtime_supplement(current_record, current_index)
    return unless current_record.needs?('location') || current_record.needs?('date_count')
    
    puts "  補完処理を実行中..."
    
    # 前後の画像から補完候補を収集
    neighbors = collect_neighbors(current_index)
    
    # 補完実行
    current_record.supplement_from_neighbors(neighbors, @time_window)
  end
  
  # 前後の画像を収集（補完元として使用）
  def collect_neighbors(current_index)
    neighbors = []
    
    # 前の画像（最大3件）
    start_idx = [0, current_index - 3].max
    (start_idx...current_index).each do |i|
      neighbors << @results[i] if @results[i]
    end
    
    neighbors
  end
  
  # 撮影時刻順にソート
  def sort_by_capture_time(image_paths)
    # 各画像の撮影時刻を取得してソート
    images_with_time = image_paths.map do |path|
      time = ExifReader.capture_time_with_fallback(path)
      [path, time || Time.at(0)]  # 時刻が取得できない場合は古い日時を設定
    end
    
    # 撮影時刻順でソート
    images_with_time.sort_by { |_, time| time }.map { |path, _| path }
  end
  
  # 結果をファイルに保存
  # @param output_path [String] 出力ファイルパス
  def save_results(output_path)
    results_hash = @results.map(&:to_hash)
    
    File.open(output_path, 'w') do |file|
      file.write(JSON.pretty_generate(results_hash))
    end
    
    puts "\n結果を保存しました: #{output_path}"
  end
  
  # 結果をコンソールに表示
  def display_results
    puts "\n=== 処理結果サマリー ==="
    
    @results.each_with_index do |record, index|
      puts "\n#{index + 1}. #{File.basename(record.image_path)}"
      
      # 撮影時刻
      if record.capture_time
        time_str = record.capture_time.strftime('%H:%M')
        puts "   撮影時刻: #{time_str}"
      end
      
      # 測点情報
      location_info = build_location_info(record)
      puts "   #{location_info}" if location_info
      
      # 日付・台数情報
      date_count_info = build_date_count_info(record)
      puts "   #{date_count_info}" if date_count_info
      
      # エラー情報
      if record.ocr_skipped
        puts "   エラー: #{record.ocr_skip_reason}"
      end
    end
    
    SurveyPoint.print_statistics(@results)
  end
  
  private
  
  # 単一結果の表示
  def display_result(record)
    location_info = build_location_info(record)
    date_count_info = build_date_count_info(record)
    
    info_parts = [location_info, date_count_info].compact
    
    if record.ocr_skipped
      puts "  結果: エラー (#{record.ocr_skip_reason})"
    elsif info_parts.empty?
      puts "  結果: 抽出値なし"
    else
      puts "  結果: #{info_parts.join(', ')}"
    end
  end
  
  # 測点情報の表示文字列を構築
  def build_location_info(record)
    original_loc = record.location_value
    inferred_loc = record.inferred_location
    
    if original_loc && !SurveyPoint.incomplete_location?(original_loc)
      # 完全な測点情報がある場合
      "場所: #{original_loc}"
    elsif inferred_loc
      # 推定された測点情報がある場合
      "場所: #{inferred_loc}(推定) ※要確認"
    elsif original_loc
      # 不完全だが測点情報がある場合
      "場所: #{original_loc}(不完全)"
    else
      nil
    end
  end
  
  # 日付・台数情報の表示文字列を構築
  def build_date_count_info(record)
    date_val = record.date_value
    count_val = record.count_value
    inferred_date_count = record.inferred_date_count
    
    if date_val && count_val
      "日付: #{date_val}, 台数: #{count_val}"
    elsif inferred_date_count
      # 推定された日付・台数情報を表示
      parts = inferred_date_count.split('|')
      if parts.size == 2
        "推定結果: 日付: #{parts[0]}, 台数: #{parts[1]}"
      else
        "推定結果: #{inferred_date_count}"
      end
    elsif date_val
      "日付: #{date_val}"
    elsif count_val
      "台数: #{count_val}"
    else
      nil
    end
  end
  
  # Python互換: SurveyPoint配列を ImageEntryList に変換
  def image_entries
    return @image_entries if @image_entries
    require_relative 'image_entry'
    entries = @results.map { |sp| ImageEntry.from_survey_point(sp) }
    @image_entries = ImageEntryList.new(entries: entries, group_type: 'caption_board_images')
  end
end
