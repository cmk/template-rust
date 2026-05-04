//! layer: parse
//! depends-on:
//!
//! CLI argument parsing layer.

pub fn feature_tag() -> &'static str {
    #[cfg(feature = "core")]
    {
        "with core"
    }
    #[cfg(not(feature = "core"))]
    {
        "core disabled"
    }
}
