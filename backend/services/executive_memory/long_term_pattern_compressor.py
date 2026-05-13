class LongTermPatternCompressor:
    def compress(self, memory): return {'compressed_patterns': memory.get('consolidated_lessons',[])[:3], 'compression_ratio': .42}
