import LoadingSkeleton from "../ui/LoadingSkeleton";

function SkeletonCard({ lines = 3 }) {
    return <LoadingSkeleton variant="card" count={1} lines={lines} label="Loading dashboard content" />;
}

export default SkeletonCard;

