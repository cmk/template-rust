#![forbid(unsafe_code)]

//! Public facade namespace for this workspace.
//!
//! Implementation crates stay split for build hygiene, while this crate
//! presents the template as a nested API:
//!
//! - [`core`] for shared core types, layer roots, and test utilities.

#[cfg(feature = "core")]
pub mod core {
    //! Shared core primitives and test utilities.

    pub use core_impl::*;
}

#[cfg(test)]
mod tests {
    #[cfg(feature = "core")]
    #[test]
    fn project_facade_core_namespace_compiles() {
        let path = crate::core::testing::fixture_or_skip(
            env!("CARGO_MANIFEST_DIR"),
            "__missing_fixture__",
        );
        assert!(path.is_none());
    }
}
