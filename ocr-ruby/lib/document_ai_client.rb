require 'json'
require 'digest'
require 'fileutils'
require 'pathname'

# DocumentAI はオプショナル（デモモード用）
begin
  require 'google/cloud/document_ai'
  DOCUMENTAI_AVAILABLE = true
rescue LoadError
  DOCUMENTAI_AVAILABLE = false
end

# Google Cloud DocumentAI を使用したOCR処理クライアント
class DocumentAIClient
  attr_reader :client, :processor_name, :demo_mode
    def initialize(config_path = nil)
    @config = load_config(config_path)
    @demo_mode = should_use_demo_mode?
    
    if @demo_mode
      puts "デモモードで実行します（ダミーOCRデータを使用）"
      @client = nil
      @processor_name = nil
    else
      setup_production_client
    end
  end
  # 画像からテキストを抽出
  # @param image_path [String] 画像ファイルのパス
  # @return [Hash] OCR結果のハッシュ
  def extract_text(image_path)
    # --- キャッシュパス ---
    cache_dirs = [PY_CACHE_DIR, RB_CACHE_DIR]
    cache_path = nil
    cache_dirs.each do |dir|
      path = _cache_path_for(image_path, dir)
      if File.exist?(path)
        cache_path = path
        break
      end
    end

    # キャッシュヒット
    if cache_path && File.exist?(cache_path)
      begin
        cached = JSON.parse(File.read(cache_path, encoding: 'utf-8'))

        # --- ここで値抽出ロジックを最新版で再実行 ---
        if cached['ocr_text']
          require_relative 'caption_board_value_extractor'
          boxes = nil
          if cached['document'] && cached['document']['pages']
            boxes = []
            doc = cached['document']
            text = doc['text'] || cached['ocr_text']
            (doc['pages'] || []).each do |page|
              (page['blocks'] || []).each do |blk|
                segs = blk.dig('layout', 'textAnchor', 'textSegments')
                next unless segs && !segs.empty?
                start_idx = segs.first['startIndex'].to_i rescue 0
                end_idx   = segs.first['endIndex'].to_i rescue 0
                txt = text[start_idx...end_idx].to_s.strip
                next if txt.empty?
                verts = blk.dig('layout', 'boundingPoly', 'vertices') || []
                # 有効な頂点(x,y が数値)を検索
                v_valid = verts.find { |v| v['x'] && v['y'] }
                v_valid ||= verts.first || {}
                x_coord = v_valid['x']
                y_coord = v_valid['y']
                next if x_coord.nil? || y_coord.nil?
                # 0,0 のダミー座標のみはスキップ
                next if x_coord.to_i.zero? && y_coord.to_i.zero?

                boxes << { 'text' => txt, 'x' => x_coord.to_i, 'y' => y_coord.to_i }
              end
            end
          end

          if boxes && !boxes.empty?
            extracted = CaptionBoardValueExtractor.extract(boxes)
            cached['location_value'] = extracted['location_value']
            cached['date_value'] = extracted['date_value']
            cached['count_value'] = extracted['count_value']
          else
            # 座標付きボックスが無い場合は値抽出しない
            cached['location_value'] = nil
            cached['date_value'] = nil
            cached['count_value'] = nil
          end
        end

        cached['from_cache'] = true
        puts "[CACHE] OCRキャッシュヒット: #{File.basename(image_path)} (値を再抽出)"
        return cached
      rescue JSON::ParserError
        # 壊れたキャッシュは無視して再OCR
        warn "[CACHE] 壊れたキャッシュを無視: #{cache_path}"
      end
    end

    unless File.exist?(image_path)
      return create_error_result(image_path, "ファイルが存在しません")
    end
    
    # デモモードの場合はダミーデータを返す
    if @demo_mode
      demo_res = generate_demo_result(image_path)
      _save_cache(demo_res.merge('from_cache' => false), _cache_path_for(image_path, PY_CACHE_DIR))
      return demo_res
    end
    
    begin
      # ファイル読み込み
      image_content = File.binread(image_path)
      mime_type = detect_mime_type(image_path)
      
      puts "OCR処理中: #{File.basename(image_path)}"
      
      # DocumentAI リクエスト作成
      request = {
        name: @processor_name,
        raw_document: {
          content: image_content,
          mime_type: mime_type
        }
      }
      
      # DocumentAI API 呼び出し
      response = @client.process_document(request)
      document = response.document
      
      # 結果を解析
      result_hash = parse_document_result(image_path, document)
      result_hash['from_cache'] = false
      _save_cache(result_hash, _cache_path_for(image_path, PY_CACHE_DIR))
      result_hash
      
    rescue => e
      puts "OCRエラー (#{File.basename(image_path)}): #{e.message}"
      err_res = create_error_result(image_path, e.message)
      _save_cache(err_res.merge('from_cache' => false), _cache_path_for(image_path, PY_CACHE_DIR))
      err_res
    end
  end
  
  private
    # 設定ファイルを読み込み
  def load_config(config_path)
    config_path ||= File.join(__dir__, '../config/document_ai.json')
    
    if File.exist?(config_path)
      config = JSON.parse(File.read(config_path))
      puts "設定ファイルを読み込みました: #{config_path}"
      config
    else
      puts "設定ファイルが見つかりません: #{config_path}"
      puts "環境変数から設定を取得を試行..."
      
      # 環境変数から設定を取得
      env_config = {
        'project_id' => ENV['GOOGLE_CLOUD_PROJECT_ID'],
        'location' => ENV['DOCUMENT_AI_LOCATION'] || 'us',
        'processor_id' => ENV['DOCUMENT_AI_PROCESSOR_ID'],
        'credentials_path' => ENV['GOOGLE_APPLICATION_CREDENTIALS']
      }
      
      if env_config['project_id'] && env_config['processor_id']
        puts "環境変数から設定を取得しました"
        env_config
      else
        puts "環境変数にも必要な設定が見つかりません"
        nil
      end
    end
  rescue JSON::ParserError => e
    puts "設定ファイルのJSON解析エラー: #{e.message}"
    nil
  end
    # プロセッサー名を構築
  def build_processor_name
    project_id = @config['project_id']
    location = @config['location']
    processor_id = @config['processor_id']
    
    unless project_id && location && processor_id
      raise "DocumentAI設定が不完全です。config/document_ai.json を確認してください。"
    end
    
    # Ruby版DocumentAI gemでの正しいプロセッサー名形式
    "projects/#{project_id}/locations/#{location}/processors/#{processor_id}"
  end
  
  # ファイル拡張子からMIMEタイプを推定
  def detect_mime_type(file_path)
    ext = File.extname(file_path).downcase
    case ext
    when '.jpg', '.jpeg'
      'image/jpeg'
    when '.png'
      'image/png'
    when '.pdf'
      'application/pdf'
    else
      'image/jpeg'  # デフォルト
    end
  end
    # DocumentAI の結果を解析してハッシュに変換
  def parse_document_result(image_path, document)
    # --- Document.text / blocks → lines と boxes へ分解 ---
    ocr_text = document.text || ""
    lines = ocr_text.split("\n").map(&:strip)

    texts_with_boxes = []
    begin
      (document.pages || []).each do |page|
        (page.blocks || []).each do |blk|
          seg = blk.layout.text_anchor.text_segments.first
          start_idx = seg.respond_to?(:start_index) ? seg.start_index.to_i : 0
          end_idx   = seg.end_index.to_i
          txt = ocr_text[start_idx...end_idx].to_s.strip
          next if txt.empty?
          verts = blk.dig('layout', 'boundingPoly', 'vertices') || []
          # 有効な頂点(x,y が数値)を検索
          v_valid = verts.find { |v| v['x'] && v['y'] }
          v_valid ||= verts.first || {}
          x_coord = v_valid['x']
          y_coord = v_valid['y']
          next if x_coord.nil? || y_coord.nil?
          # 0,0 のダミー座標のみはスキップ
          next if x_coord.to_i.zero? && y_coord.to_i.zero?

          texts_with_boxes << { "text" => txt, "x" => x_coord.to_i, "y" => y_coord.to_i }
        end
      end
    rescue StandardError
      texts_with_boxes = []
    end

    extracted = if texts_with_boxes.empty?
                   CaptionBoardValueExtractor.extract(lines)
                 else
                   CaptionBoardValueExtractor.extract(texts_with_boxes)
                 end

    puts "OCR抽出テキスト: #{ocr_text[0, 60]}#{'...' if ocr_text.length > 60}"

    {
      'image_path' => image_path,
      'ocr_text' => ocr_text,
      'location_value' => extracted['location_value'],
      'date_value' => extracted['date_value'],
      'count_value' => extracted['count_value'],
      'confidence' => 0.9,
      'error' => nil,
      'capture_time' => nil
    }
  end
  
  # バウンディングボックス情報を抽出
  def extract_bounding_box(entity)
    return nil unless entity.page_anchor&.page_refs&.first&.bounding_box
    
    bbox = entity.page_anchor.page_refs.first.bounding_box
    vertices = bbox.vertices
    
    return nil unless vertices && vertices.size >= 4
    
    x_coords = vertices.map(&:x).compact
    y_coords = vertices.map(&:y).compact
    
    return nil if x_coords.empty? || y_coords.empty?
    
    {
      'x1' => x_coords.min,
      'y1' => y_coords.min,
      'x2' => x_coords.max,
      'y2' => y_coords.max,
      'width' => x_coords.max - x_coords.min,
      'height' => y_coords.max - y_coords.min
    }
  end
    # パターンマッチングによるテキスト抽出
  def extract_by_patterns(result)
    text = result['ocr_text'] || ""
    
    puts "パターンマッチング対象テキスト: #{text[0..100]}#{'...' if text.length > 100}"
    
    # --------------------------
    # 場所 / 測点 抽出
    #   ・「場所 XXX」形式
    #   ・「測点 No.26」形式
    #   ・主要地名（市町村名）
    # --------------------------
    location_patterns = [
      /場所[:\s]*([^\s\n]+)/,               # 場所 XXX
      /測点[:\s]*(No\.?\s*\d+)/i,          # 測点 No.26
      /(小山|宇都宮|那須塩原|大田原|足利|佐野|栃木|真岡|矢板|塩谷|鹿沼|日光|さくら|那須烏山|下野)/
    ]
    
    location_patterns.each do |pattern|
      match = text.match(pattern)
      if match && !result['location_value']
        result['location_value'] = match[1] || match[0]
        puts "場所抽出: #{result['location_value']}"
        break
      end
    end
    
    # --------------------------
    # 日付 抽出
    # --------------------------
    date_patterns = [
      /日付[:\s]*(\d{1,2}[\/\-]\d{1,2})/,      # 日付 5/30
      /(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})/,    # 2024/05/30
      /(\d{1,2}[\/\-]\d{1,2})/                  # 5/30, 5-30
    ]
    
    date_patterns.each do |pattern|
      match = text.match(pattern)
      if match && !result['date_value']
        result['date_value'] = match[1] || match[0]
        puts "日付抽出: #{result['date_value']}"
        break
      end
    end
    
    # --------------------------
    # 台数 抽出
    # --------------------------
    count_patterns = [
      /台数[:\s]*(\d+台目?)/,          # 台数 1台目
      /台数[:\s]*(\d+\s*台)/,          # 台数 5台
      /(\d+台目?)/,                      # 1台目
      /(\d+\s*台)/                      # 5台
    ]
    
    count_patterns.each do |pattern|
      match = text.match(pattern)
      if match && !result['count_value']
        result['count_value'] = match[1] || match[0]
        puts "台数抽出: #{result['count_value']}"
        break
      end
    end
  end
  
  # エラー結果を作成
  def create_error_result(image_path, error_message)
    {
      'filename' => File.basename(image_path),
      'image_path' => image_path,
      'capture_time' => Time.now,
      'bbox' => nil,
      'location_value' => nil,
      'date_value' => nil,
      'count_value' => nil,
      'ocr_skipped' => true,
      'ocr_skip_reason' => error_message,
      'raw_text' => '',
      'entities' => []
    }
  end

  # デモモード用のダミーOCRデータ生成
  def generate_demo_result(image_path)
    filename = File.basename(image_path, '.*')
    
    # ファイル名から番号を抽出してパターンを決定
    number = filename.scan(/\d+/).last.to_i
    
    # ダミーデータのパターン
    demo_patterns = [
      {
        text: "No.1 小山 5/30 1台目",
        location_value: "小山",
        date_value: "5/30",
        count_value: "1台目"
      },
      {
        text: "No.2 大田原 5/30 2台目",
        location_value: "大田原",
        date_value: "5/30",
        count_value: "2台目"
      },
      {
        text: "No.3 那須塩原 6/1 1台目",
        location_value: "那須塩原",
        date_value: "6/1",
        count_value: "1台目"
      },
      {
        text: "No.4 宇都宮 6/1 3台目",
        location_value: "宇都宮",
        date_value: "6/1",
        count_value: "3台目"
      },
      {
        text: "No.",  # 不完全データ（補完対象）
        location_value: nil,
        date_value: nil,
        count_value: nil
      },
      {
        text: "小山",  # 場所のみ（補完対象）
        location_value: "小山",
        date_value: nil,
        count_value: nil
      }
    ]
    
    # ファイル番号に応じてパターンを選択
    pattern_index = (number % demo_patterns.size)
    pattern = demo_patterns[pattern_index]
    
    puts "デモOCR結果: #{File.basename(image_path)} -> '#{pattern[:text]}'"
    
    {
      'image_path' => image_path,
      'ocr_text' => pattern[:text],
      'location_value' => pattern[:location_value],
      'date_value' => pattern[:date_value],
      'count_value' => pattern[:count_value],
      'confidence' => 0.85,
      'error' => nil,
      'capture_time' => nil  # ExifReaderで後で設定される
    }
  end

  # デモモードを使用するかどうかを判定
  def should_use_demo_mode?
    # DocumentAIライブラリが利用できない場合
    return true unless DOCUMENTAI_AVAILABLE
    
    # 設定が不完全な場合
    return true if @config.nil? || @config.empty?
    
    required_keys = ['project_id', 'location', 'processor_id']
    missing_keys = required_keys.select { |key| @config[key].nil? || @config[key].empty? }
    
    return true unless missing_keys.empty?
    
    # プレースホルダー値の場合（実際の設定ではない）
    placeholder_values = ['your-gcp-project-id', 'your-processor-id']
    return true if placeholder_values.include?(@config['project_id']) || 
                   placeholder_values.include?(@config['processor_id'])
    
    false
  end
    # 本番クライアントをセットアップ
  def setup_production_client
    puts "DocumentAI本番モードを初期化中..."
    puts "プロジェクト: #{@config['project_id']}"
    puts "リージョン: #{@config['location']}"
    puts "プロセッサー: #{@config['processor_id']}"
    
    begin
      # 認証情報の設定
      setup_credentials
      
      # DocumentAIクライアント作成
      @client = Google::Cloud::DocumentAI.document_processor_service do |config|
        if @credentials_path && File.exist?(@credentials_path)
          config.credentials = @credentials_path
        end
      end
      
      @processor_name = build_processor_name
      
      puts "DocumentAI接続テスト中..."
      test_connection
      
      puts "DocumentAI初期化完了"
    rescue => e
      puts "DocumentAI初期化エラー: #{e.message}"
      puts "デモモードにフォールバック"
      @demo_mode = true
      @client = nil
      @processor_name = nil
    end
  end
    # 認証情報をセットアップ
  def setup_credentials
    @credentials_path = @config['credentials_path']
    
    if @credentials_path && File.exist?(@credentials_path)
      puts "サービスアカウントキーを使用: #{@credentials_path}"
      # 認証ファイルをクライアント作成時に指定
    elsif ENV['GOOGLE_APPLICATION_CREDENTIALS']
      puts "環境変数のサービスアカウントキーを使用"
      @credentials_path = ENV['GOOGLE_APPLICATION_CREDENTIALS']
    else
      puts "デフォルト認証を使用（gcloud auth application-default login）"
      @credentials_path = nil
    end
  end
    # 接続テスト
  def test_connection
    # プロセッサー情報を取得してみる
    begin
      response = @client.get_processor(name: @processor_name)
      puts "プロセッサー名: #{response.display_name}"
      puts "プロセッサータイプ: #{response.type}"
    rescue => e
      raise "DocumentAI接続テストに失敗: #{e.message}"
    end
  end

  # キャッシュパス生成
  def _cache_path_for(image_path, cache_dir)
    digest = Digest::MD5.hexdigest(File.absolute_path(image_path))
    File.join(cache_dir, "#{digest}.json")
  end

  # キャッシュ保存
  def _save_cache(result_hash, cache_path)
    File.write(cache_path, JSON.pretty_generate(result_hash), mode: 'w', encoding: 'utf-8')
  rescue StandardError => e
    warn "[CACHE] キャッシュ保存失敗: #{e.message}"
  end

  ROOT_DIR = Pathname.new(__dir__).join('..', '..').expand_path.freeze
  PY_CACHE_DIR = ROOT_DIR.join('ocr_tools', 'ocr_cache').to_s.freeze
  RB_CACHE_DIR = ROOT_DIR.join('ocr-ruby', 'ocr_cache').to_s.freeze
end
