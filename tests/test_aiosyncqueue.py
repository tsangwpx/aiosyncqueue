import asyncio
import logging

import pytest

import aiosyncqueue

TIMEOUT_EPSILON = 1e-6


async def sleep_for_cycles(n=1):
    for _ in range(n if n >= 0 else 1):
        await asyncio.sleep(0)


def assert_future_done_normally(fut: asyncio.Future):
    assert fut.done(), fut
    assert not fut.cancelled(), fut
    assert fut.exception() is None


@pytest.fixture
def queue_factory(caplog):
    caplog.set_level(logging.DEBUG)

    def __queue_factory():
        return aiosyncqueue.SyncQueue()

    return __queue_factory


@pytest.mark.asyncio
async def test_sq_put_get(queue_factory):
    q = queue_factory()

    put1 = asyncio.create_task(q.put(1))
    put2 = asyncio.create_task(q.put(2))
    put3 = asyncio.create_task(q.put(3))

    result = await asyncio.wait_for(q.get(), TIMEOUT_EPSILON)
    assert result is 1

    result = await asyncio.wait_for(q.get(), TIMEOUT_EPSILON)
    assert result is 2

    result = await asyncio.wait_for(q.get(), TIMEOUT_EPSILON)
    assert result is 3

    assert put1.done() and not put1.cancelled(), put1
    assert put2.done() and not put2.cancelled(), put2
    assert put3.done() and not put3.cancelled(), put3


@pytest.mark.asyncio
async def test_sq_put_get_nowait(queue_factory):
    q = queue_factory()

    fs = [
        asyncio.create_task(q.put(1)),
        asyncio.create_task(q.put(2)),
        asyncio.create_task(q.put(3)),
    ]

    # Schedule the puts
    await asyncio.sleep(0)

    assert q.get_nowait() is 1
    assert q.get_nowait() is 2
    assert q.get_nowait() is 3

    await asyncio.wait(fs, timeout=0)


@pytest.mark.asyncio
async def test_sq_put_nowait_get(queue_factory):
    q = queue_factory()

    get1 = asyncio.create_task(q.get())
    get2 = asyncio.create_task(q.get())
    get3 = asyncio.create_task(q.get())

    # Schedule the gets
    await asyncio.sleep(0)

    q.put_nowait(1)
    q.put_nowait(2)
    q.put_nowait(3)

    result = await get1
    assert result is 1

    result = await get2
    assert result is 2

    result = await get3
    assert result is 3


@pytest.mark.asyncio
async def test_sq_queue_full(queue_factory):
    q = queue_factory()

    with pytest.raises(asyncio.QueueFull):
        q.put_nowait(None)


@pytest.mark.asyncio
async def test_sq_queue_empty(queue_factory):
    q = queue_factory()

    with pytest.raises(asyncio.QueueEmpty):
        q.get_nowait()


@pytest.mark.asyncio
async def test_sq_get_cancellation(queue_factory, caplog):
    caplog.set_level(logging.DEBUG)

    logging.debug('get, cancel, sleep, put_nowait')
    q1 = queue_factory()
    get1 = asyncio.create_task(q1.get())
    assert get1.cancel()
    await asyncio.sleep(0)
    # get1 has no change to run but throw CancellationError directly
    # getter is not scheduled
    with pytest.raises(asyncio.CancelledError):
        await get1
    with pytest.raises(asyncio.QueueFull):
        q1.put_nowait(1)

    logging.debug('get, sleep, cancel, put_nowait')
    q2 = queue_factory()
    get2 = asyncio.create_task(q2.get())
    await asyncio.sleep(0)
    # get2 await on a getter
    assert get2.cancel()
    # the getter (q._getters[0]._fut_waiter) is cancelled
    with pytest.raises(asyncio.QueueFull):
        q2.put_nowait(None)

    assert not get2.cancelled()
    await asyncio.sleep(0)
    # CancellationError is thrown when stepping get2
    with pytest.raises(asyncio.CancelledError):
        await get2

    logging.debug('put, get, cancel, sleep')
    q3 = queue_factory()
    put3 = asyncio.create_task(q3.put(3))
    get3 = asyncio.create_task(q3.get())
    assert get3.cancel()
    await asyncio.sleep(0)
    with pytest.raises(asyncio.CancelledError):
        await get3
    assert q3.get_nowait() is 3
    await asyncio.sleep(0)
    assert_future_done_normally(put3)

    await put3

    logging.debug('put, get, sleep, cancel')
    q4 = queue_factory()
    put4 = asyncio.create_task(q4.put(4))
    get4 = asyncio.create_task(q4.get())
    await asyncio.sleep(0)
    # get() have taken 4 from put4 so get4 is done now
    assert get4.done() and not get4.cancel()
    assert_future_done_normally(get4)
    # put4 is updated in one more cycle
    await asyncio.sleep(0)
    assert_future_done_normally(put4)


@pytest.mark.asyncio
async def test_sq_put_cancellation(queue_factory, caplog):
    caplog.set_level(logging.DEBUG)

    logging.debug('..., put, cancel, ...')
    q1 = queue_factory()
    get1a = asyncio.create_task(q1.get())
    put1 = asyncio.create_task(q1.put(1))
    get1b = asyncio.create_task(q1.get())
    assert put1.cancel()
    await asyncio.sleep(0)
    assert put1.cancelled()
    assert get1a.cancel()
    assert get1b.cancel()

    logging.debug('get, put, sleep, cancel')
    q2 = queue_factory()
    get2 = asyncio.create_task(q2.get())
    put2 = asyncio.create_task(q2.put(2))
    await asyncio.sleep(0)
    # get2's getter took the item
    assert put2.done()
    await asyncio.sleep(0)
    assert get2.done()

    logging.debug('put, sleep, cancel, get')
    q3 = queue_factory()
    put3 = asyncio.create_task(q3.put(3))
    await asyncio.sleep(0)
    assert put3.cancel()
    assert not put3.cancelled()
    with pytest.raises(asyncio.CancelledError):
        await put3


@pytest.mark.asyncio
async def test_sq_cancellation(queue_factory, caplog):
    caplog.set_level(logging.DEBUG)

    q1 = queue_factory()
    get1 = asyncio.create_task(q1.get())
    put1 = asyncio.create_task(q1.put(1))
    await asyncio.sleep(0)  # Only one cycle is allowed
    assert get1.cancel()
    await get1
    assert not get1.cancelled()
    await put1


@pytest.mark.asyncio
async def test_sq_cancellation2(queue_factory, caplog):
    caplog.set_level(logging.DEBUG)

    q1 = queue_factory()
    put1 = asyncio.create_task(q1.put(1))
    get1 = asyncio.create_task(q1.get())
    await asyncio.sleep(0)
    assert put1.cancel()
    await put1
    result = await get1
    assert result == 1
